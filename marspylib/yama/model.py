"""Object model for Mars .yama archives.

Field names and defaults are transcribed from mars-core's Java record
classes (MarsRegion, MarsPosition, MarsBdvSource, MarsDocument,
AbstractMarsRecord, AbstractMolecule, AbstractMarsMetadata,
AbstractMoleculeArchiveProperties).

Every archive type gets its own `Molecule` subclass, uniformly -- even
`SingleMolecule`/`DnaMolecule`/`DefaultMolecule`, which are currently empty
(mars-core's classes are structurally identical: ctor-only, no extra
fields). This is deliberate future-proofing: mars-core could add
type-specific fields to any of these later (as it already has for
`MartianObject`'s `shapes` and `TransverseFlowMolecule`'s
`replication_fork_shapes`), and having the class already exist means that's
an additive change here too, not a restructuring. `ARCHIVE_TO_MOLECULE_CLASS`
is what `io/molecule.py` uses to pick which class to build for a given
archive.

`Molecule`/`MarsMetadata` (and their subclasses) auto-generate a UID in
mars-core's own format if none is given -- matching mars-core's own
no-arg constructors, which do exactly this (AbstractMolecule.java:96,
AbstractMarsMetadata.java:101). Parsing an existing archive still generates
one of these per record, immediately overwritten by the real UID read from
the file -- wasteful, but that's what the Java constructors do too.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Iterator

import pandas as pd

from .uid import new_metadata_uid, new_molecule_uid

DEFAULT_ARCHIVE_TYPE = "de.mpg.biochem.mars.molecule.SingleMoleculeArchive"
CURRENT_SCHEMA = "2022-04-11"

ARCHIVE_TYPES = {
    "SingleMoleculeArchive": "de.mpg.biochem.mars.molecule.SingleMoleculeArchive",
    "DnaMoleculeArchive": "de.mpg.biochem.mars.molecule.DnaMoleculeArchive",
    "DefaultMoleculeArchive": "de.mpg.biochem.mars.molecule.DefaultMoleculeArchive",
    "ObjectArchive": "de.mpg.biochem.mars.object.ObjectArchive",
    "TransverseFlowArchive": "de.mpg.biochem.mars.transverseflow.TransverseFlowArchive",
}

# Each archive type fixes its own concrete Molecule subtype (M in mars-core's
# generic MoleculeArchive<M, I, P, X>) -- used to write the write-only "type"
# field on each molecule record.
ARCHIVE_TO_MOLECULE_TYPE = {
    "de.mpg.biochem.mars.molecule.SingleMoleculeArchive": "de.mpg.biochem.mars.molecule.SingleMolecule",
    "de.mpg.biochem.mars.molecule.DnaMoleculeArchive": "de.mpg.biochem.mars.molecule.DnaMolecule",
    "de.mpg.biochem.mars.molecule.DefaultMoleculeArchive": "de.mpg.biochem.mars.molecule.DefaultMolecule",
    "de.mpg.biochem.mars.object.ObjectArchive": "de.mpg.biochem.mars.object.MartianObject",
    "de.mpg.biochem.mars.transverseflow.TransverseFlowArchive": "de.mpg.biochem.mars.transverseflow.TransverseFlowMolecule",
}

# MarsOMEMetadata is the only concrete MarsMetadata used by every archive type.
METADATA_TYPE_FQCN = "de.mpg.biochem.mars.metadata.MarsOMEMetadata"


@dataclass
class MarsRegion:
    name: str = "Region"
    column: str = "T"
    color: str = "#416ef468"
    start: float = 0.0
    end: float = 0.0
    opacity: float = 0.2


@dataclass
class MarsPosition:
    name: str = "Position"
    column: str = "T"
    color: str = "#000000"
    stroke: float = 1.0
    position: float = 0.0


@dataclass
class MarsBdvSource:
    name: str = ""
    is_n5: bool = False
    drift_correct: bool = False
    path: str = ""
    dataset: str = ""
    channel: int = 0
    single_time_point_mode: bool = False
    single_time_point: int = 0
    # row-major 3x4 affine transform, matching net.imglib2.realtransform.AffineTransform3D's layout
    affine_transform: tuple[float, ...] = (1.0, 0.0, 0.0, 0.0,
                                            0.0, 1.0, 0.0, 0.0,
                                            0.0, 0.0, 1.0, 0.0)
    properties: dict[str, str] = field(default_factory=dict)


@dataclass
class MarsDocument:
    name: str = ""
    content: str = ""
    media: dict[str, str] = field(default_factory=dict)
    media_array: dict[str, list[str]] = field(default_factory=dict)


@dataclass
class MarsRecord:
    """Fields shared by every Molecule and MarsMetadata record."""
    uid: str = ""
    notes: str | None = None
    tags: list[str] = field(default_factory=list)
    parameters: dict[str, float | str | bool] = field(default_factory=dict)
    regions: dict[str, MarsRegion] = field(default_factory=dict)
    positions: dict[str, MarsPosition] = field(default_factory=dict)
    # fields present in the source archive that this reader doesn't know about
    # are preserved here (name -> generic decoded value) and re-emitted on write
    extra: dict[str, Any] = field(default_factory=dict)

    def has_tag(self, tag: str) -> bool:
        return tag in self.tags

    def add_tag(self, tag: str) -> None:
        if tag not in self.tags:
            self.tags.append(tag)

    def has_region(self, name: str) -> bool:
        return name in self.regions

    def has_position(self, name: str) -> bool:
        return name in self.positions

    def get_position(self, name: str) -> MarsPosition | None:
        return self.positions.get(name)

    def get_region(self, name: str) -> MarsRegion | None:
        return self.regions.get(name)


@dataclass
class Molecule(MarsRecord):
    uid: str = field(default_factory=new_molecule_uid)
    table: pd.DataFrame = field(default_factory=pd.DataFrame)
    metadata_uid: str = ""
    image: int = -1
    channel: int = -1
    # keyed by (x_column, y_column, region) -- region is "" when none was set
    segment_tables: dict[tuple[str, str, str], pd.DataFrame] = field(default_factory=dict)


@dataclass
class SingleMolecule(Molecule):
    """Used by SingleMoleculeArchive. Currently identical to Molecule."""


@dataclass
class DnaMolecule(Molecule):
    """Used by DnaMoleculeArchive. Currently identical to Molecule."""


@dataclass
class DefaultMolecule(Molecule):
    """Used by DefaultMoleculeArchive. Currently identical to Molecule."""


@dataclass
class PeakShape:
    """A closed 2D polygon outline (image/PeakShape.java) -- x/y coordinate
    arrays, always the same length ("vertices" on disk is just that length,
    redundant with len(x)/len(y) and not kept separately here)."""
    x: list[float] = field(default_factory=list)
    y: list[float] = field(default_factory=list)


@dataclass
class MartianObject(Molecule):
    """Used by ObjectArchive (mars-core's `object` package). Adds one field
    beyond plain Molecule: a PeakShape polygon per timepoint."""
    shapes: dict[int, PeakShape] = field(default_factory=dict)


@dataclass
class ReplicationForkShape:
    """A DNA replication fork's geometry (mars-transverseflow's
    ReplicationForkShape.java): three polygon/polyline segments -- the
    not-yet-replicated parental duplex, and the leading/lagging daughter
    strands -- each with an optional per-channel intensity profile sampled
    along the shape (channel name -> {coordinate: intensity}). Note the real
    Java quirk, preserved here rather than "fixed": parental/leading
    intensity samples are keyed by "x", lagging by "y" -- see io/transverseflow.py."""
    parental_x: list[float] = field(default_factory=list)
    parental_y: list[float] = field(default_factory=list)
    parental_intensity: dict[str, dict[int, float]] = field(default_factory=dict)
    leading_x: list[float] = field(default_factory=list)
    leading_y: list[float] = field(default_factory=list)
    leading_intensity: dict[str, dict[int, float]] = field(default_factory=dict)
    lagging_x: list[float] = field(default_factory=list)
    lagging_y: list[float] = field(default_factory=list)
    lagging_intensity: dict[str, dict[int, float]] = field(default_factory=dict)


@dataclass
class TransverseFlowMolecule(Molecule):
    """Used by TransverseFlowArchive (the separate mars-transverseflow
    module). Adds one field beyond plain Molecule: a ReplicationForkShape
    per timepoint."""
    replication_fork_shapes: dict[int, ReplicationForkShape] = field(default_factory=dict)


# Which dataclass to instantiate for a given archive's molecule records.
ARCHIVE_TO_MOLECULE_CLASS = {
    "de.mpg.biochem.mars.molecule.SingleMoleculeArchive": SingleMolecule,
    "de.mpg.biochem.mars.molecule.DnaMoleculeArchive": DnaMolecule,
    "de.mpg.biochem.mars.molecule.DefaultMoleculeArchive": DefaultMolecule,
    "de.mpg.biochem.mars.object.ObjectArchive": MartianObject,
    "de.mpg.biochem.mars.transverseflow.TransverseFlowArchive": TransverseFlowMolecule,
}


@dataclass
class MarsMetadata(MarsRecord):
    uid: str = field(default_factory=new_metadata_uid)
    microscope: str = "unknown"
    source_directory: str = "unknown"
    log: str = ""
    bdv_sources: dict[str, MarsBdvSource] = field(default_factory=dict)
    # OME image metadata, kept as a generic decoded tree rather than a typed
    # model -- MarsOMEImage is a large structure and modeling it isn't the
    # point of this port; this round-trips losslessly.
    images: list[Any] = field(default_factory=list)

    def has_tag(self, tag: str) -> bool:
        return tag in self.tags


@dataclass
class Properties:
    archive_type: str = DEFAULT_ARCHIVE_TYPE
    schema: str = CURRENT_SCHEMA
    number_of_molecules: int = 0
    number_of_metadata: int = 0
    table_column_set: set[str] = field(default_factory=set)
    # each entry is (x_column, y_column)
    segment_table_names: set[tuple[str, str]] = field(default_factory=set)
    tag_set: set[str] = field(default_factory=set)
    channel_set: set[int] = field(default_factory=set)
    parameter_set: set[str] = field(default_factory=set)
    region_set: set[str] = field(default_factory=set)
    position_set: set[str] = field(default_factory=set)
    documents: dict[str, MarsDocument] = field(default_factory=dict)


class Archive:
    """In-memory, eagerly-loaded single-file .yama archive.

    Access only ever goes through __iter__/__getitem__/__contains__/.metadata
    (never the backing dicts) so a future lazy .yama.store loader can be
    swapped in behind this same public surface without a breaking change.
    """

    def __init__(self, properties: Properties, metadata: dict[str, MarsMetadata],
                 molecules: dict[str, Molecule], source_path: Path | None = None):
        self.properties = properties
        self._metadata = metadata
        self._molecules = molecules
        self._source_path = source_path

    @property
    def archive_type(self) -> str:
        return self.properties.archive_type

    def __len__(self) -> int:
        return len(self._molecules)

    def __iter__(self) -> Iterator[Molecule]:
        return iter(self._molecules.values())

    def __getitem__(self, uid: str) -> Molecule:
        return self._molecules[uid]

    def __contains__(self, uid: str) -> bool:
        return uid in self._molecules

    @property
    def metadata(self) -> Iterator[MarsMetadata]:
        return iter(self._metadata.values())

    def get_metadata(self, uid: str) -> MarsMetadata | None:
        return self._metadata.get(uid)

    def metadata_has_tag(self, metadata_uid: str, tag: str) -> bool:
        meta = self._metadata.get(metadata_uid)
        return meta is not None and meta.has_tag(tag)

    def put(self, molecule: Molecule) -> None:
        """Add a new molecule (keyed by molecule.uid), or replace an
        existing one. For a plain in-memory archive this is just a dict
        write and mutating a molecule you already hold a reference to
        (e.g. archive["x"].add_tag(...)) already persists without calling
        put() at all. For a .yama.store-backed archive, put() matters more:
        molecules are lazily loaded and LRU-cached, so a mutated molecule
        that falls out of cache before save() would otherwise be silently
        re-read from disk, losing the edit -- put() pins it so it's
        guaranteed to survive to the next save(), and is also the only way
        to add a UID that wasn't already in the archive."""
        self._molecules[molecule.uid] = molecule

    def put_metadata(self, metadata: MarsMetadata) -> None:
        """Add a new metadata record, or replace an existing one. See put()
        -- metadata is already fully cached once loaded (never evicted), so
        this mainly matters for adding a UID that wasn't already present."""
        self._metadata[metadata.uid] = metadata

    def _sync_properties_before_save(self) -> None:
        """Recomputes properties' aggregate fields from the archive's
        current contents, mirroring mars-core's rebuildIndexes()/
        AbstractMoleculeArchiveProperties.addMoleculeProperties (a fresh
        scan of every present molecule, not an incremental merge) --
        without this, put()-ing a molecule with a new tag/parameter/channel
        would leave the saved archive's properties stale. Note
        addMetadataProperties is a no-op in mars-core itself ("currently
        nothing is indexed") so metadata contributes nothing here either,
        and channel -1 (mars-core's "unset" sentinel) is excluded from
        channel_set, matching addMoleculeProperties exactly."""
        tag_set: set[str] = set()
        channel_set: set[int] = set()
        parameter_set: set[str] = set()
        region_set: set[str] = set()
        position_set: set[str] = set()
        table_column_set: set[str] = set()
        segment_table_names: set[tuple[str, str]] = set()

        for molecule in self:
            tag_set.update(molecule.tags)
            parameter_set.update(molecule.parameters.keys())
            region_set.update(molecule.regions.keys())
            position_set.update(molecule.positions.keys())
            if molecule.channel > -1:
                channel_set.add(molecule.channel)
            table_column_set.update(str(c) for c in molecule.table.columns)
            for x_col, y_col, _region in molecule.segment_tables.keys():
                segment_table_names.add((x_col, y_col))

        self.properties.number_of_molecules = len(self)
        self.properties.number_of_metadata = len(list(self.metadata))
        self.properties.tag_set = tag_set
        self.properties.channel_set = channel_set
        self.properties.parameter_set = parameter_set
        self.properties.region_set = region_set
        self.properties.position_set = position_set
        self.properties.table_column_set = table_column_set
        self.properties.segment_table_names = segment_table_names

    def save(self, path: str | Path | None = None) -> None:
        """Write this archive out. If `path` is omitted, reuses the path it
        was opened from. Whether the result is a single-file .yama or a
        .yama.store virtual archive is decided purely by whether `target`'s
        name ends in ".yama.store" -- so opening a virtual store and calling
        .save() with no args updates it in place, .save("out.yama") flattens
        it into one file, and .save("out.yama.store") on a single-file-backed
        archive creates a new virtual store, all through the same method."""
        from .io.store import looks_like_virtual_store_path, write_virtual_store

        target = Path(path) if path is not None else self._source_path
        if target is None:
            raise ValueError("no path given and archive was not opened from a file")

        self._sync_properties_before_save()

        if looks_like_virtual_store_path(target):
            write_virtual_store(target, self)
        else:
            from .io.archive import write_archive_document
            from .smile.writer import SmileWriter

            with open(target, "wb") as stream:
                writer = SmileWriter(stream)
                writer.write_header()
                write_archive_document(writer, self)
                writer.close()
        self._source_path = target
