"""Storage backends for .yama.store virtual archives: a small Store protocol
(read/write/exists/delete/list, all keyed by a path relative to some root)
that the virtual-store machinery in io/store.py is written against, plus a
local-filesystem implementation and an S3 (or any S3-compatible endpoint)
one. Mirrors mars-core's own MoleculeArchiveSource interface, which the same
two concrete implementations (filesystem, S3) exist for on the Java side.

Single-file .yama archives don't go through this -- they're one blob, read/
written directly (see yama/__init__.py's open()/open_s3() and
model.py's Archive.save()/save_s3()) -- Store only matters for the
multi-key .yama.store layout (properties, indexes, one file per record).
"""

from __future__ import annotations

from pathlib import Path
from typing import Protocol

from .s3 import S3Location


class Store(Protocol):
    def read_bytes(self, key: str) -> bytes: ...
    def write_bytes(self, key: str, data: bytes) -> None: ...
    def exists(self, key: str) -> bool: ...
    def delete(self, key: str) -> None: ...
    def list_keys(self, prefix: str) -> list[str]:
        """Non-recursive: only keys directly under `prefix` (which should
        end in "/"), not nested further -- matching a plain directory
        listing. Returned keys are relative to the store's own root, same
        as every other method here, so they can be fed straight back into
        read_bytes()/exists()/delete()."""
        ...


class LocalFilesystemStore:
    def __init__(self, root: Path):
        self.root = root

    def _path(self, key: str) -> Path:
        return self.root / key

    def read_bytes(self, key: str) -> bytes:
        return self._path(key).read_bytes()

    def write_bytes(self, key: str, data: bytes) -> None:
        path = self._path(key)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(data)

    def exists(self, key: str) -> bool:
        return self._path(key).exists()

    def delete(self, key: str) -> None:
        path = self._path(key)
        if path.exists():
            path.unlink()

    def list_keys(self, prefix: str) -> list[str]:
        directory = self._path(prefix)
        if not directory.is_dir():
            return []
        norm_prefix = prefix if prefix.endswith("/") else f"{prefix}/"
        return [f"{norm_prefix}{p.name}" for p in directory.iterdir() if p.is_file()]


def _require_boto3():
    try:
        import boto3
    except ImportError as exc:
        raise ImportError(
            "S3 support requires boto3, which is an optional dependency of marspylib. "
            "Install it with: pip install marspylib[s3]"
        ) from exc
    return boto3


def s3_client(location: S3Location, session=None, **client_kwargs):
    """A boto3 S3 client pointed at `location`'s endpoint -- used directly
    for single-file .yama archives (one GET/PUT, no need for the full Store
    abstraction), and internally by S3Store for .yama.store archives."""
    boto3 = _require_boto3()
    session = session or boto3.Session()
    return session.client("s3", endpoint_url=location.endpoint_url, **client_kwargs)


class S3Store:
    """A Store rooted at `location.key` within `location.bucket` on the S3
    (or S3-compatible) endpoint `location.server_address`. If `session` is
    omitted, a plain `boto3.Session()` is used, which resolves credentials
    the standard boto3 way (environment variables, ~/.aws/credentials,
    ~/.aws/config, SSO cache, IAM role) -- the same local-credential
    resolution AWS SDKs use everywhere, so "credentials are already set up
    locally" needs no extra configuration here."""

    def __init__(self, location: S3Location, session=None, **client_kwargs):
        self.location = location
        self.bucket = location.bucket
        self.root_key = location.key.rstrip("/")
        self._client = s3_client(location, session=session, **client_kwargs)

    def _full_key(self, key: str) -> str:
        return f"{self.root_key}/{key}" if self.root_key else key

    def read_bytes(self, key: str) -> bytes:
        response = self._client.get_object(Bucket=self.bucket, Key=self._full_key(key))
        return response["Body"].read()

    def write_bytes(self, key: str, data: bytes) -> None:
        self._client.put_object(Bucket=self.bucket, Key=self._full_key(key), Body=data)

    def exists(self, key: str) -> bool:
        from botocore.exceptions import ClientError

        try:
            self._client.head_object(Bucket=self.bucket, Key=self._full_key(key))
            return True
        except ClientError as exc:
            if exc.response.get("Error", {}).get("Code") in ("404", "NoSuchKey"):
                return False
            raise

    def delete(self, key: str) -> None:
        self._client.delete_object(Bucket=self.bucket, Key=self._full_key(key))

    def list_keys(self, prefix: str) -> list[str]:
        full_prefix = self._full_key(prefix)
        if full_prefix and not full_prefix.endswith("/"):
            full_prefix += "/"
        strip_len = len(self.root_key) + 1 if self.root_key else 0

        keys = []
        paginator = self._client.get_paginator("list_objects_v2")
        for page in paginator.paginate(Bucket=self.bucket, Prefix=full_prefix, Delimiter="/"):
            for obj in page.get("Contents", []):
                keys.append(obj["Key"][strip_len:])
        return keys
