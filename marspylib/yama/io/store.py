"""Support for .yama.store virtual archives: lazy per-record loading from a
directory tree instead of one big in-memory document, and writing archives
back out in that same layout. Works against anything satisfying the `Store`
protocol (backend.py) -- a local filesystem directory or an S3 bucket/prefix
-- since neither the Smile parsing nor the index/record logic here cares
where the bytes actually come from.

Transcribed from mars-core's MoleculeArchiveFSSource (layout/UID scanning;
MoleculeArchiveAmazonS3Source uses the identical layout, just S3 keys
instead of paths), AbstractMoleculeArchiveIndex (indexes.<ext> shape and
addMolecule/addMetadata population), and AbstractMoleculeArchive.
loadVirtualStore/rebuildIndexes/saveAsVirtualStore (read/write order and
missing-index fallback). Only the Smile ('.sml') encoding is supported,
matching this port's single-file scope.

Each file in the store (MoleculeArchiveProperties.sml, indexes.sml, and
every per-record Molecules/<uid>.sml / Metadata/<uid>.sml) is its own
independent Smile document with its own 4-byte header -- mars-core opens a
fresh SmileGenerator/SmileParser per file, so each is read/written exactly
like a tiny single-file .yama.
"""

from __future__ import annotations

from collections import OrderedDict
from dataclasses import dataclass, field
from pathlib import Path

from ..backend import LocalFilesystemStore, S3Store, Store
from ..errors import YamaFormatError
from ..model import ARCHIVE_TO_MOLECULE_TYPE, Archive, MarsMetadata, Molecule
from ..s3 import S3Location
from ..smile.reader import SmileReader, SmileToken
from ..smile.writer import SmileWriter
from .metadata import read_metadata, write_metadata
from .molecule import read_molecule, write_molecule
from .properties import read_properties, write_properties

PROPERTIES_FILE_NAME = "MoleculeArchiveProperties"
INDEXES_FILE_NAME = "indexes"
MOLECULES_SUBDIRECTORY_NAME = "Molecules"
METADATA_SUBDIRECTORY_NAME = "Metadata"
STORE_FILE_EXTENSION = ".sml"

DEFAULT_MOLECULE_CACHE_SIZE = 128


def is_virtual_store(path: Path) -> bool:
    return path.is_dir() and path.name.endswith(".yama.store")


def looks_like_virtual_store_path(path: Path) -> bool:
    """Like is_virtual_store, but for a save target that may not exist yet."""
    return path.name.endswith(".yama.store")


def _detect_extension(store: Store) -> str:
    if store.exists(f"{PROPERTIES_FILE_NAME}.sml"):
        return ".sml"
    if store.exists(f"{PROPERTIES_FILE_NAME}.json"):
        raise YamaFormatError(
            "this .yama.store archive uses the plain-JSON virtual store encoding, which is "
            "not supported (only Smile-encoded '.sml' virtual stores are supported)"
        )
    raise YamaFormatError(f"no {PROPERTIES_FILE_NAME}.sml found")


def _read_document_root(data: bytes) -> SmileReader:
    reader = SmileReader(data)
    tok = reader.next_token()
    if tok != SmileToken.START_OBJECT:
        raise YamaFormatError(f"expected top-level START_OBJECT, got {tok}")
    return reader


def _scan_uids(store: Store, prefix: str, ext: str) -> list[str]:
    return sorted(
        key[len(prefix):-len(ext)]
        for key in store.list_keys(prefix)
        if key.endswith(ext)
    )


@dataclass
class MoleculeIndexEntry:
    """The denormalized per-molecule data AbstractMoleculeArchiveIndex keeps
    for predicate-pushdown lookups (tags/channel/image/metadataUID) without
    needing to load the full record -- mirrors what mars-core's index
    actually carries (see AbstractMoleculeArchiveIndex.addMolecule)."""
    tags: list[str] = field(default_factory=list)
    channel: int = -1
    image: int = -1
    metadata_uid: str | None = None


def _read_index(reader: SmileReader) -> tuple[dict[str, list[str]], dict[str, MoleculeIndexEntry]]:
    """Parses indexes.<ext> (AbstractMoleculeArchiveIndex.createIOMaps: a root
    object with "metadata" and "molecules" arrays). Returns
    (metadata_index: uid -> tags, molecule_index: uid -> MoleculeIndexEntry),
    both insertion-ordered (Python dicts preserve this) matching file order."""
    metadata_index: dict[str, list[str]] = {}
    molecule_index: dict[str, MoleculeIndexEntry] = {}

    while True:
        tok = reader.next_token()
        if tok == SmileToken.END_OBJECT:
            break
        if tok != SmileToken.FIELD_NAME:
            raise YamaFormatError(f"expected FIELD_NAME or END_OBJECT in indexes document, got {tok}")
        name = reader.current_name()
        reader.next_token()  # advance onto the array's START_ARRAY
        if name == "metadata":
            metadata_index.update(_read_metadata_index_entries(reader))
        elif name == "molecules":
            molecule_index.update(_read_molecule_index_entries(reader))
        else:
            reader.skip_value()

    return metadata_index, molecule_index


def _read_metadata_index_entries(reader: SmileReader) -> dict[str, list[str]]:
    result: dict[str, list[str]] = {}
    while True:
        tok = reader.next_token()
        if tok == SmileToken.END_ARRAY:
            return result
        uid = None
        tags: list[str] = []
        while True:
            tok2 = reader.next_token()
            if tok2 == SmileToken.END_OBJECT:
                break
            field_name = reader.current_name()
            reader.next_token()
            if field_name == "uid":
                uid = reader.get_text()
            elif field_name == "tags":
                while True:
                    tok3 = reader.next_token()
                    if tok3 == SmileToken.END_ARRAY:
                        break
                    tags.append(reader.get_text())
            else:
                reader.skip_value()
        if uid is not None:
            result[uid] = tags


def _read_molecule_index_entries(reader: SmileReader) -> dict[str, MoleculeIndexEntry]:
    result: dict[str, MoleculeIndexEntry] = {}
    while True:
        tok = reader.next_token()
        if tok == SmileToken.END_ARRAY:
            return result
        uid = None
        entry = MoleculeIndexEntry()
        while True:
            tok2 = reader.next_token()
            if tok2 == SmileToken.END_OBJECT:
                break
            field_name = reader.current_name()
            value_tok = reader.next_token()
            if field_name == "uid":
                uid = reader.get_text()
            elif field_name == "metadataUID":
                entry.metadata_uid = reader.get_text() if value_tok == SmileToken.VALUE_STRING else None
            elif field_name == "tags":
                while True:
                    tok3 = reader.next_token()
                    if tok3 == SmileToken.END_ARRAY:
                        break
                    entry.tags.append(reader.get_text())
            elif field_name == "channel":
                entry.channel = reader.get_int()
            elif field_name == "image":
                entry.image = reader.get_int()
            else:
                reader.skip_value()
        if uid is not None:
            result[uid] = entry


class _LazyMoleculeMap:
    """Molecule access is not cached by mars-core itself (only lock-guarded
    against concurrent same-UID reads) -- every AbstractMoleculeArchive.get()
    call re-reads the file. An LRU cache is added here instead: single-writer
    notebook usage benefits far more from not re-parsing a molecule every
    time it's touched than it risks staleness.

    That LRU cache can still evict a read-only access, which is fine -- it's
    just re-read next time (from disk, or over the network for S3). `put()`
    (via `__setitem__`) is different: it's an explicit "this must be saved"
    pin, kept in `_overrides` where it can never be evicted, checked before
    the LRU cache on every read. This is also how a brand-new UID gets added
    to the archive."""

    def __init__(self, store: Store, archive_type: str, uids: list[str],
                 cache_size: int = DEFAULT_MOLECULE_CACHE_SIZE,
                 index: dict[str, MoleculeIndexEntry] | None = None):
        self._store = store
        self._key_prefix = f"{MOLECULES_SUBDIRECTORY_NAME}/"
        self._archive_type = archive_type
        self._uids = uids
        self._uid_set = set(uids)
        self._cache: "OrderedDict[str, Molecule]" = OrderedDict()
        self._cache_size = cache_size
        self._overrides: dict[str, Molecule] = {}
        # From indexes.<ext> if one was present at open time -- lets
        # tags_for()/channel_for()/etc. answer without loading the full
        # record. Never rewritten after open (put()/remove() invalidate the
        # relevant entry instead of trying to patch it), and entirely absent
        # when the store had no index file to begin with (directory-scan
        # fallback), in which case every lookup just falls back to a load.
        self._index: dict[str, MoleculeIndexEntry] = index or {}

    def _key(self, uid: str) -> str:
        return f"{self._key_prefix}{uid}{STORE_FILE_EXTENSION}"

    def _load(self, uid: str) -> Molecule:
        reader = _read_document_root(self._store.read_bytes(self._key(uid)))
        return read_molecule(reader, self._archive_type)

    def __getitem__(self, uid: str) -> Molecule:
        if uid in self._overrides:
            return self._overrides[uid]
        if uid not in self._uid_set:
            raise KeyError(uid)
        if uid in self._cache:
            self._cache.move_to_end(uid)
            return self._cache[uid]
        molecule = self._load(uid)
        self._cache[uid] = molecule
        if len(self._cache) > self._cache_size:
            self._cache.popitem(last=False)
        return molecule

    def __setitem__(self, uid: str, molecule: Molecule) -> None:
        if uid not in self._uid_set:
            self._uid_set.add(uid)
            self._uids.append(uid)
        self._overrides[uid] = molecule
        self._cache.pop(uid, None)
        # The old index entry (if any) no longer reflects this molecule's
        # current tags/channel/image -- drop it so lookups fall back to the
        # override object itself instead of serving stale data.
        self._index.pop(uid, None)

    def __delitem__(self, uid: str) -> None:
        """Matches mars-core's remove(): deletes the underlying .sml file
        immediately (not deferred to the next save()) -- see
        MoleculeArchiveFSSource.removeMolecule()/
        MoleculeArchiveAmazonS3Source's equivalent."""
        if uid not in self._uid_set:
            raise KeyError(uid)
        self._uid_set.discard(uid)
        self._uids.remove(uid)
        self._cache.pop(uid, None)
        self._overrides.pop(uid, None)
        self._index.pop(uid, None)
        self._store.delete(self._key(uid))

    def __contains__(self, uid: str) -> bool:
        return uid in self._uid_set

    def __len__(self) -> int:
        return len(self._uids)

    def __iter__(self):
        return iter(self._uids)

    def uids(self) -> list[str]:
        return list(self._uids)

    def values(self):
        for uid in self._uids:
            yield self[uid]

    def items(self):
        for uid in self._uids:
            yield uid, self[uid]

    def get(self, uid: str, default=None):
        try:
            return self[uid]
        except KeyError:
            return default

    # -- predicate-pushdown lookups: answer from the index when possible,
    # without loading the full record. Priority is overrides > cache > index
    # > full load: anything already resident in memory is more current than
    # a (possibly stale, e.g. after a put() elsewhere) index entry.

    def tags_for(self, uid: str) -> list[str]:
        if uid not in self._uid_set:
            raise KeyError(uid)
        if uid in self._overrides:
            return list(self._overrides[uid].tags)
        if uid in self._cache:
            return list(self._cache[uid].tags)
        entry = self._index.get(uid)
        if entry is not None:
            return list(entry.tags)
        return list(self[uid].tags)

    def channel_for(self, uid: str) -> int:
        if uid not in self._uid_set:
            raise KeyError(uid)
        if uid in self._overrides:
            return self._overrides[uid].channel
        if uid in self._cache:
            return self._cache[uid].channel
        entry = self._index.get(uid)
        if entry is not None:
            return entry.channel
        return self[uid].channel

    def image_for(self, uid: str) -> int:
        if uid not in self._uid_set:
            raise KeyError(uid)
        if uid in self._overrides:
            return self._overrides[uid].image
        if uid in self._cache:
            return self._cache[uid].image
        entry = self._index.get(uid)
        if entry is not None:
            return entry.image
        return self[uid].image

    def metadata_uid_for(self, uid: str) -> str | None:
        if uid not in self._uid_set:
            raise KeyError(uid)
        if uid in self._overrides:
            return self._overrides[uid].metadata_uid
        if uid in self._cache:
            return self._cache[uid].metadata_uid
        entry = self._index.get(uid)
        if entry is not None:
            return entry.metadata_uid
        return self[uid].metadata_uid


class _LazyMetadataMap:
    """Matches mars-core: once loaded, a metadata record stays resident for
    the life of the archive (metadata sets are small -- typically one per
    source image -- unlike molecules, which can number in the thousands).
    Since nothing here is ever evicted, `put()` (via `__setitem__`) is just
    a cache write -- no separate override/pin tier is needed like it is for
    `_LazyMoleculeMap`."""

    def __init__(self, store: Store, uids: list[str],
                 index: dict[str, list[str]] | None = None):
        self._store = store
        self._key_prefix = f"{METADATA_SUBDIRECTORY_NAME}/"
        self._uids = uids
        self._uid_set = set(uids)
        self._cache: dict[str, MarsMetadata] = {}
        self._index: dict[str, list[str]] = index or {}  # uid -> tags, from indexes.<ext>

    def _key(self, uid: str) -> str:
        return f"{self._key_prefix}{uid}{STORE_FILE_EXTENSION}"

    def _load(self, uid: str) -> MarsMetadata:
        reader = _read_document_root(self._store.read_bytes(self._key(uid)))
        return read_metadata(reader)

    def __getitem__(self, uid: str) -> MarsMetadata:
        if uid not in self._uid_set:
            raise KeyError(uid)
        if uid not in self._cache:
            self._cache[uid] = self._load(uid)
        return self._cache[uid]

    def __setitem__(self, uid: str, metadata: MarsMetadata) -> None:
        if uid not in self._uid_set:
            self._uid_set.add(uid)
            self._uids.append(uid)
        self._cache[uid] = metadata
        self._index.pop(uid, None)

    def __delitem__(self, uid: str) -> None:
        """Matches mars-core's removeMetadata(): deletes the underlying
        .sml file immediately -- see MoleculeArchiveFSSource.removeMetadata()."""
        if uid not in self._uid_set:
            raise KeyError(uid)
        self._uid_set.discard(uid)
        self._uids.remove(uid)
        self._cache.pop(uid, None)
        self._index.pop(uid, None)
        self._store.delete(self._key(uid))

    def __contains__(self, uid: str) -> bool:
        return uid in self._uid_set

    def __len__(self) -> int:
        return len(self._uids)

    def __iter__(self):
        return iter(self._uids)

    def uids(self) -> list[str]:
        return list(self._uids)

    def values(self):
        for uid in self._uids:
            yield self[uid]

    def items(self):
        for uid in self._uids:
            yield uid, self[uid]

    def get(self, uid: str, default=None):
        try:
            return self[uid]
        except KeyError:
            return default

    def tags_for(self, uid: str) -> list[str]:
        if uid not in self._uid_set:
            raise KeyError(uid)
        if uid in self._cache:  # never evicted, so if present it's authoritative
            return list(self._cache[uid].tags)
        entry = self._index.get(uid)
        if entry is not None:
            return list(entry)
        return list(self[uid].tags)


def _open_virtual_store(store: Store, source_path,
                         molecule_cache_size: int = DEFAULT_MOLECULE_CACHE_SIZE) -> Archive:
    """Generic open, working against any Store -- see open_virtual_store()
    (local filesystem) and open_virtual_store_s3() for the concrete entry
    points. `source_path` is whatever Archive.save()/save_s3() should
    remember as "where this came from" (a Path or an S3Location)."""
    ext = _detect_extension(store)

    properties = read_properties(_read_document_root(store.read_bytes(f"{PROPERTIES_FILE_NAME}{ext}")))
    if properties.archive_type not in ARCHIVE_TO_MOLECULE_TYPE:
        raise YamaFormatError(
            f"unsupported archiveType {properties.archive_type!r}; "
            f"expected one of {sorted(ARCHIVE_TO_MOLECULE_TYPE)}"
        )

    index_key = f"{INDEXES_FILE_NAME}{ext}"
    if store.exists(index_key):
        metadata_index, molecule_index = _read_index(_read_document_root(store.read_bytes(index_key)))
        molecule_uids = list(molecule_index.keys())
        metadata_uids = list(metadata_index.keys())
    else:
        # mars-core rebuilds the index here by fully loading every record;
        # this just scans filenames instead and lets records load lazily --
        # so tags_for()/channel_for()/etc. have no index to answer from and
        # fall back to a full load until the next save() rewrites indexes.<ext>.
        molecule_uids = _scan_uids(store, f"{MOLECULES_SUBDIRECTORY_NAME}/", ext)
        metadata_uids = _scan_uids(store, f"{METADATA_SUBDIRECTORY_NAME}/", ext)
        molecule_index = {}
        metadata_index = {}

    molecules = _LazyMoleculeMap(store, properties.archive_type, molecule_uids,
                                  cache_size=molecule_cache_size, index=molecule_index)
    metadata = _LazyMetadataMap(store, metadata_uids, index=metadata_index)

    return Archive(properties, metadata, molecules, source_path=source_path)


def open_virtual_store(store_dir: Path, molecule_cache_size: int = DEFAULT_MOLECULE_CACHE_SIZE) -> Archive:
    return _open_virtual_store(LocalFilesystemStore(store_dir), store_dir,
                                molecule_cache_size=molecule_cache_size)


def open_virtual_store_s3(location: S3Location, session=None,
                           molecule_cache_size: int = DEFAULT_MOLECULE_CACHE_SIZE,
                           **client_kwargs) -> Archive:
    store = S3Store(location, session=session, **client_kwargs)
    return _open_virtual_store(store, location, molecule_cache_size=molecule_cache_size)


def _write_record_document(store: Store, key: str, write_fn) -> None:
    import io as _io

    buf = _io.BytesIO()
    writer = SmileWriter(buf)
    writer.write_header()
    write_fn(writer)
    writer.close()
    store.write_bytes(key, buf.getvalue())


def _write_index(store: Store, ext: str, archive: Archive) -> None:
    """Mirrors AbstractMoleculeArchiveIndex.createIOMaps's write order
    ("metadata" array, then "molecules" array) and addMolecule/addMetadata's
    unconditional population -- every field is always written, matching what
    a freshly rebuilt index actually contains (see module docstring)."""

    def write(writer: SmileWriter) -> None:
        writer.write_start_object()

        writer.write_field_name("metadata")
        writer.write_start_array()
        for meta in archive.metadata:
            writer.write_start_object()
            writer.write_field_name("uid")
            writer.write_string(meta.uid)
            writer.write_field_name("tags")
            writer.write_start_array()
            for tag in meta.tags:
                writer.write_string(tag)
            writer.write_end_array()
            writer.write_end_object()
        writer.write_end_array()

        writer.write_field_name("molecules")
        writer.write_start_array()
        for molecule in archive:
            writer.write_start_object()
            writer.write_field_name("uid")
            writer.write_string(molecule.uid)
            writer.write_field_name("metadataUID")
            writer.write_string(molecule.metadata_uid)
            writer.write_field_name("tags")
            writer.write_start_array()
            for tag in molecule.tags:
                writer.write_string(tag)
            writer.write_end_array()
            writer.write_field_name("channel")
            writer.write_int(molecule.channel)
            writer.write_field_name("image")
            writer.write_int(molecule.image)
            writer.write_end_object()
        writer.write_end_array()

        writer.write_end_object()

    _write_record_document(store, f"{INDEXES_FILE_NAME}{ext}", write)


def _write_virtual_store(store: Store, archive: Archive) -> None:
    """Generic write, working against any Store -- see write_virtual_store()
    (local filesystem) and write_virtual_store_s3() for the concrete entry
    points.

    Mirrors mars-core's saveAsVirtualStore order: every metadata and molecule
    record file first, then indexes.<ext>, then MoleculeArchiveProperties.<ext>
    last. Iterating `archive` here forces every record to be loaded (lazily,
    from wherever it currently lives) so the written store is always a
    complete, self-consistent snapshot -- not just whatever happened to be
    cached.
    """
    for meta in archive.metadata:
        _write_record_document(store, f"{METADATA_SUBDIRECTORY_NAME}/{meta.uid}{STORE_FILE_EXTENSION}",
                                lambda w, m=meta: write_metadata(w, m))

    for molecule in archive:
        _write_record_document(store, f"{MOLECULES_SUBDIRECTORY_NAME}/{molecule.uid}{STORE_FILE_EXTENSION}",
                                lambda w, mol=molecule: write_molecule(w, mol, archive.archive_type))

    _write_index(store, STORE_FILE_EXTENSION, archive)

    _write_record_document(store, f"{PROPERTIES_FILE_NAME}{STORE_FILE_EXTENSION}",
                            lambda w: write_properties(w, archive.properties))


def write_virtual_store(store_dir: Path, archive: Archive) -> None:
    _write_virtual_store(LocalFilesystemStore(store_dir), archive)


def write_virtual_store_s3(location: S3Location, archive: Archive, session=None, **client_kwargs) -> None:
    store = S3Store(location, session=session, **client_kwargs)
    _write_virtual_store(store, archive)
