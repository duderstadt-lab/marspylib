"""Pure-Python reader/writer for Mars MoleculeArchive .yama files. ::

    import marspylib.yama as yama

    archive = yama.open("experiment.yama")
    archive.properties.number_of_molecules
    for molecule in archive:
        df = molecule.table            # pandas.DataFrame
        if "accepted" in molecule.tags:
            ...
    molecule = archive["some-uid"]     # random access by UID
    archive.save("experiment_out.yama")

`yama.open()` also accepts a `.yama.store` virtual archive directory, in
which case records are loaded lazily on access rather than all at once.
Since not-yet-accessed records are only read from disk the moment you touch
them, the store directory must still exist at that point -- don't move,
delete, or let a temporary directory holding one go out of scope while an
Archive opened from it is still in use.
"""

from __future__ import annotations

from pathlib import Path

from .errors import SmileFormatError, UnsupportedSchemaError, YamaFormatError
from .model import (
    ARCHIVE_TYPES,
    Archive,
    DefaultMolecule,
    DnaMolecule,
    MarsBdvSource,
    MarsDocument,
    MarsMetadata,
    MarsPosition,
    MarsRegion,
    MartianObject,
    Molecule,
    PeakShape,
    Properties,
    ReplicationForkShape,
    SingleMolecule,
    TransverseFlowMolecule,
)
from .s3 import S3Location
from .uid import new_metadata_uid, new_molecule_uid


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


def open_s3(location: S3Location | str | None = None, *, server_address: str | None = None,
            bucket: str | None = None, key: str | None = None, secure: bool = True,
            session=None, molecule_cache_size: int | None = None, **client_kwargs) -> Archive:
    """Read a .yama (or lazily open a .yama.store) archive from S3 or any
    S3-compatible endpoint. The location can be given either as the three
    fields separately (recommended -- unambiguous):

        archive = yama.open_s3(server_address="s3.example-storage.org",
                                bucket="my-bucket", key="path/to/experiment.yama")

    or as a single combined virtual-hosted-style URL, for compatibility with
    setups that already use that convention:

        archive = yama.open_s3("https://my-bucket.s3.example-storage.org/path/to/experiment.yama")

    Credentials are resolved the standard boto3 way (environment variables,
    ~/.aws/credentials, SSO cache, IAM role) -- if they're already configured
    locally, nothing further needs to be passed here. Pass `session=` (a
    boto3.Session) to override that resolution explicitly."""
    from .io.store import open_virtual_store_s3
    from .s3 import resolve_s3_location

    resolved = resolve_s3_location(location, server_address=server_address, bucket=bucket,
                                    key=key, secure=secure)

    if resolved.key.endswith(".yama.store"):
        kwargs = {}
        if molecule_cache_size is not None:
            kwargs["molecule_cache_size"] = molecule_cache_size
        return open_virtual_store_s3(resolved, session=session, **kwargs, **client_kwargs)

    from .backend import s3_client
    from .io.archive import read_archive_document
    from .smile.reader import SmileReader

    client = s3_client(resolved, session=session, **client_kwargs)
    data = client.get_object(Bucket=resolved.bucket, Key=resolved.key)["Body"].read()
    reader = SmileReader(data)
    archive = read_archive_document(reader)
    archive._source_path = resolved
    return archive


__all__ = [
    "open", "write", "open_s3",
    "Archive", "Molecule", "MarsMetadata", "MarsRegion", "MarsPosition",
    "MarsBdvSource", "MarsDocument", "Properties", "ARCHIVE_TYPES",
    "SingleMolecule", "DnaMolecule", "DefaultMolecule",
    "MartianObject", "PeakShape",
    "TransverseFlowMolecule", "ReplicationForkShape",
    "new_molecule_uid", "new_metadata_uid",
    "S3Location",
    "YamaFormatError", "SmileFormatError", "UnsupportedSchemaError",
]
