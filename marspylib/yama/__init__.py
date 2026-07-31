"""Pure-Python reader/writer for Mars MoleculeArchive .yama files.

    import marspylib.yama as yama

    archive = yama.open("experiment.yama")
    archive.properties.number_of_molecules
    for molecule in archive:
        df = molecule.table            # pandas.DataFrame
        if "accepted" in molecule.tags:
            ...
    molecule = archive["some-uid"]     # random access by UID
    archive.save("experiment_out.yama")
"""

from __future__ import annotations

from pathlib import Path

from .errors import SmileFormatError, UnsupportedSchemaError, YamaFormatError
from .model import (
    Archive,
    MarsBdvSource,
    MarsDocument,
    MarsMetadata,
    MarsPosition,
    MarsRegion,
    Molecule,
    Properties,
)


def open(path: str | Path) -> Archive:
    """Read a .yama archive into memory, or lazily open a .yama.store
    virtual archive (a directory of per-record files) -- dispatched on
    whether `path` is a directory."""
    from .io.store import is_virtual_store, open_virtual_store

    p = Path(path)
    if is_virtual_store(p):
        return open_virtual_store(p)

    from .io.archive import read_archive_document
    from .smile.reader import SmileReader

    reader = SmileReader(p.read_bytes())
    archive = read_archive_document(reader)
    archive._source_path = p
    return archive


def write(archive: Archive, path: str | Path) -> None:
    """Write `archive` to a single-file .yama at `path`."""
    archive.save(path)


__all__ = [
    "open", "write",
    "Archive", "Molecule", "MarsMetadata", "MarsRegion", "MarsPosition",
    "MarsBdvSource", "MarsDocument", "Properties",
    "YamaFormatError", "SmileFormatError", "UnsupportedSchemaError",
]
