"""Object model for Mars .yama archives.

Field names and defaults are transcribed from mars-core's Java record
classes (MarsRegion, MarsPosition, MarsBdvSource, MarsDocument,
AbstractMarsRecord, AbstractMolecule, AbstractMarsMetadata,
AbstractMoleculeArchiveProperties). `SingleMolecule`/`DnaMolecule`/
`DefaultMolecule` are structurally identical in mars-core (ctor-only, no
extra fields) so one `Molecule` dataclass covers all three -- the archive's
own `Properties.archive_type` is the only discriminator needed.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Iterator

import pandas as pd

DEFAULT_ARCHIVE_TYPE = "de.mpg.biochem.mars.molecule.SingleMoleculeArchive"
CURRENT_SCHEMA = "2022-04-11"

ARCHIVE_TYPES = {
    "SingleMoleculeArchive": "de.mpg.biochem.mars.molecule.SingleMoleculeArchive",
    "DnaMoleculeArchive": "de.mpg.biochem.mars.molecule.DnaMoleculeArchive",
    "DefaultMoleculeArchive": "de.mpg.biochem.mars.molecule.DefaultMoleculeArchive",
}

# Each archive type fixes its own concrete Molecule subtype (M in mars-core's
# generic MoleculeArchive<M, I, P, X>) -- these subtypes are structurally
# identical (ctor-only, no extra fields), so this port uses one Molecule
# dataclass and only needs this mapping to write the write-only "type" field.
ARCHIVE_TO_MOLECULE_TYPE = {
    "de.mpg.biochem.mars.molecule.SingleMoleculeArchive": "de.mpg.biochem.mars.molecule.SingleMolecule",
    "de.mpg.biochem.mars.molecule.DnaMoleculeArchive": "de.mpg.biochem.mars.molecule.DnaMolecule",
    "de.mpg.biochem.mars.molecule.DefaultMoleculeArchive": "de.mpg.biochem.mars.molecule.DefaultMolecule",
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
    table: pd.DataFrame = field(default_factory=pd.DataFrame)
    metadata_uid: str = ""
    image: int = -1
    channel: int = -1
    # keyed by (x_column, y_column, region) -- region is "" when none was set
    segment_tables: dict[tuple[str, str, str], pd.DataFrame] = field(default_factory=dict)


@dataclass
class MarsMetadata(MarsRecord):
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
