"""Read-only support for .yama.store virtual archives: lazy per-record
loading from a directory tree instead of one big in-memory document.

Transcribed from mars-core's MoleculeArchiveFSSource (layout/UID scanning),
AbstractMoleculeArchiveIndex (indexes.<ext> shape), and
AbstractMoleculeArchive.loadVirtualStore/rebuildIndexes (read order and
missing-index fallback). Only the Smile ('.sml') encoding is supported,
matching this port's single-file scope.

Each file in the store (MoleculeArchiveProperties.sml, indexes.sml, and
every per-record Molecules/<uid>.sml / Metadata/<uid>.sml) is its own
independent Smile document with its own 4-byte header -- mars-core opens a
fresh SmileGenerator/SmileParser per file, so each is read exactly like a
tiny single-file .yama.
"""

from __future__ import annotations

from collections import OrderedDict
from pathlib import Path

from ..errors import YamaFormatError
from ..model import ARCHIVE_TO_MOLECULE_TYPE, Archive, MarsMetadata, Molecule
from ..smile.reader import SmileReader, SmileToken
from .metadata import read_metadata
from .molecule import read_molecule
from .properties import read_properties

PROPERTIES_FILE_NAME = "MoleculeArchiveProperties"
INDEXES_FILE_NAME = "indexes"
MOLECULES_SUBDIRECTORY_NAME = "Molecules"
METADATA_SUBDIRECTORY_NAME = "Metadata"
STORE_FILE_EXTENSION = ".sml"

DEFAULT_MOLECULE_CACHE_SIZE = 128


def is_virtual_store(path: Path) -> bool:
    return path.is_dir() and path.name.endswith(".yama.store")


def _detect_extension(store_dir: Path) -> str:
    if (store_dir / f"{PROPERTIES_FILE_NAME}.sml").exists():
        return ".sml"
    if (store_dir / f"{PROPERTIES_FILE_NAME}.json").exists():
        raise YamaFormatError(
            f"{store_dir} uses the plain-JSON virtual store encoding, which is not "
            "supported (only Smile-encoded '.sml' virtual stores are supported)"
        )
    raise YamaFormatError(f"no {PROPERTIES_FILE_NAME}.sml found in {store_dir}")


def _read_document_root(data: bytes) -> SmileReader:
    reader = SmileReader(data)
    tok = reader.next_token()
    if tok != SmileToken.START_OBJECT:
        raise YamaFormatError(f"expected top-level START_OBJECT, got {tok}")
    return reader


def _scan_uids(directory: Path, ext: str) -> list[str]:
    if not directory.is_dir():
        return []
    return sorted(p.name[:-len(ext)] for p in directory.iterdir() if p.name.endswith(ext))


def _read_index(reader: SmileReader) -> tuple[list[str], list[str]]:
    """Parses indexes.<ext> (AbstractMoleculeArchiveIndex.createIOMaps: a root
    object with "metadata" and "molecules" arrays). Only the UID lists are
    kept -- the denormalized tags/channel/image/metadataUID fields exist in
    mars-core purely for predicate pushdown, which this port doesn't
    implement yet; they're skipped rather than guessed at."""
    molecule_uids: list[str] = []
    metadata_uids: list[str] = []

    while True:
        tok = reader.next_token()
        if tok == SmileToken.END_OBJECT:
            break
        if tok != SmileToken.FIELD_NAME:
            raise YamaFormatError(f"expected FIELD_NAME or END_OBJECT in indexes document, got {tok}")
        name = reader.current_name()
        reader.next_token()  # advance onto the array's START_ARRAY
        if name == "metadata":
            metadata_uids.extend(_read_index_entries(reader))
        elif name == "molecules":
            molecule_uids.extend(_read_index_entries(reader))
        else:
            reader.skip_value()

    return molecule_uids, metadata_uids


def _read_index_entries(reader: SmileReader) -> list[str]:
    uids = []
    while True:
        tok = reader.next_token()
        if tok == SmileToken.END_ARRAY:
            return uids
        uid = None
        while True:
            tok2 = reader.next_token()
            if tok2 == SmileToken.END_OBJECT:
                break
            field = reader.current_name()
            reader.next_token()
            if field == "uid":
                uid = reader.get_text()
            else:
                reader.skip_value()
        if uid is not None:
            uids.append(uid)


class _LazyMoleculeMap:
    """Molecule access is not cached by mars-core itself (only lock-guarded
    against concurrent same-UID reads) -- every AbstractMoleculeArchive.get()
    call re-reads the file. An LRU cache is added here instead: single-writer
    notebook usage benefits far more from not re-parsing a molecule every
    time it's touched than it risks staleness."""

    def __init__(self, molecules_dir: Path, archive_type: str, uids: list[str],
                 cache_size: int = DEFAULT_MOLECULE_CACHE_SIZE):
        self._dir = molecules_dir
        self._archive_type = archive_type
        self._uids = uids
        self._uid_set = set(uids)
        self._cache: "OrderedDict[str, Molecule]" = OrderedDict()
        self._cache_size = cache_size

    def _load(self, uid: str) -> Molecule:
        path = self._dir / f"{uid}{STORE_FILE_EXTENSION}"
        reader = _read_document_root(path.read_bytes())
        return read_molecule(reader, self._archive_type)

    def __getitem__(self, uid: str) -> Molecule:
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

    def __contains__(self, uid: str) -> bool:
        return uid in self._uid_set

    def __len__(self) -> int:
        return len(self._uids)

    def __iter__(self):
        return iter(self._uids)

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


class _LazyMetadataMap:
    """Matches mars-core: once loaded, a metadata record stays resident for
    the life of the archive (metadata sets are small -- typically one per
    source image -- unlike molecules, which can number in the thousands)."""

    def __init__(self, metadata_dir: Path, uids: list[str]):
        self._dir = metadata_dir
        self._uids = uids
        self._uid_set = set(uids)
        self._cache: dict[str, MarsMetadata] = {}

    def _load(self, uid: str) -> MarsMetadata:
        path = self._dir / f"{uid}{STORE_FILE_EXTENSION}"
        reader = _read_document_root(path.read_bytes())
        return read_metadata(reader)

    def __getitem__(self, uid: str) -> MarsMetadata:
        if uid not in self._uid_set:
            raise KeyError(uid)
        if uid not in self._cache:
            self._cache[uid] = self._load(uid)
        return self._cache[uid]

    def __contains__(self, uid: str) -> bool:
        return uid in self._uid_set

    def __len__(self) -> int:
        return len(self._uids)

    def __iter__(self):
        return iter(self._uids)

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


def open_virtual_store(store_dir: Path, molecule_cache_size: int = DEFAULT_MOLECULE_CACHE_SIZE) -> Archive:
    ext = _detect_extension(store_dir)

    properties_path = store_dir / f"{PROPERTIES_FILE_NAME}{ext}"
    properties = read_properties(_read_document_root(properties_path.read_bytes()))
    if properties.archive_type not in ARCHIVE_TO_MOLECULE_TYPE:
        raise YamaFormatError(
            f"unsupported archiveType {properties.archive_type!r}; "
            f"expected one of {sorted(ARCHIVE_TO_MOLECULE_TYPE)}"
        )

    index_path = store_dir / f"{INDEXES_FILE_NAME}{ext}"
    molecules_dir = store_dir / MOLECULES_SUBDIRECTORY_NAME
    metadata_dir = store_dir / METADATA_SUBDIRECTORY_NAME
    if index_path.exists():
        molecule_uids, metadata_uids = _read_index(_read_document_root(index_path.read_bytes()))
    else:
        # mars-core rebuilds the index here by fully loading every record;
        # this just scans filenames instead and lets records load lazily.
        molecule_uids = _scan_uids(molecules_dir, ext)
        metadata_uids = _scan_uids(metadata_dir, ext)

    molecules = _LazyMoleculeMap(molecules_dir, properties.archive_type, molecule_uids,
                                  cache_size=molecule_cache_size)
    metadata = _LazyMetadataMap(metadata_dir, metadata_uids)

    return Archive(properties, metadata, molecules, source_path=store_dir)
