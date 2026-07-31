"""S3 (or any S3-compatible endpoint) location handling for .yama archives.

An archive on S3 is identified by three things: the endpoint host
(`server_address`, e.g. "storage.example.org" -- an institutional/self-hosted
S3-compatible endpoint works exactly like AWS itself here, just with a
different host), the `bucket`, and the `key` (the path to the .yama file or
.yama.store "directory" within the bucket). `S3Location` holds these three
explicitly -- the recommended way to construct one, since it can't be
misread the way a combined URL sometimes can -- and also parses/produces the
combined virtual-hosted-style URL some setups use historically
(`https://<bucket>.s3.<server_address>/<key>`), so both forms are supported.

The literal ".s3." between bucket and server_address in that combined form
is a fixed separator token -- it just marks "this is S3" -- and is *not*
necessarily part of the real endpoint host: e.g. for an archive actually
served from `minio.example.org:9000`, the combined URL is
`https://<bucket>.s3.minio.example.org:9000/<key>`, and `server_address` is
`minio.example.org:9000`, not `s3.minio.example.org:9000`. (AWS's own S3 is
a case where the real endpoint host, `s3.amazonaws.com`, separately happens
to also start with "s3." -- that's a coincidence of AWS's own naming, not
something this parsing relies on.)
"""

from __future__ import annotations

from dataclasses import dataclass
from urllib.parse import urlsplit


@dataclass
class S3Location:
    server_address: str
    bucket: str
    key: str
    secure: bool = True

    def __post_init__(self) -> None:
        address = self.server_address.strip("/")
        # server_address is meant to be a bare host[:port] (see endpoint_url
        # below) -- but a "https://" or "http://" prefix is a natural enough
        # thing to paste in here that it's worth accepting rather than
        # silently producing a broken doubled-up scheme in endpoint_url. An
        # explicit scheme here overrides `secure`.
        if address.startswith("https://"):
            self.secure = True
            address = address[len("https://"):]
        elif address.startswith("http://"):
            self.secure = False
            address = address[len("http://"):]
        self.server_address = address.strip("/")
        self.key = self.key.lstrip("/")

    @property
    def scheme(self) -> str:
        return "https" if self.secure else "http"

    @property
    def endpoint_url(self) -> str:
        """The URL to hand to an S3 client as `endpoint_url` -- no bucket,
        no key, just scheme + host."""
        return f"{self.scheme}://{self.server_address}"

    @property
    def virtual_hosted_url(self) -> str:
        """The combined `https://<bucket>.s3.<server_address>/<key>` form --
        ".s3." is a fixed separator token here, not part of server_address
        (see module docstring)."""
        return f"{self.scheme}://{self.bucket}.s3.{self.server_address}/{self.key}"

    @classmethod
    def from_url(cls, url: str) -> "S3Location":
        """Parses a combined virtual-hosted-style URL
        (`https://<bucket>.s3.<server_address>/<key>`) -- the bucket is the
        first hostname label, the second must literally be "s3" (a fixed
        separator, not part of the real endpoint host), and everything after
        that is the server address."""
        parts = urlsplit(url)
        if not parts.scheme or not parts.netloc:
            raise ValueError(
                f"not a valid S3 URL (expected https://<bucket>.s3.<server_address>/<key>): {url!r}"
            )
        bucket, sep, server_address = parts.netloc.partition(".")
        server_address_sep, _, server_address = server_address.partition(".")
        if not sep or server_address_sep.lower() != "s3" or not server_address:
            raise ValueError(
                f"S3 URL host {parts.netloc!r} doesn't look like "
                f"<bucket>.s3.<server_address> (expected "
                f"https://<bucket>.s3.<server_address>/<key>): {url!r}"
            )
        return cls(
            server_address=server_address,
            bucket=bucket,
            key=parts.path,
            secure=parts.scheme == "https",
        )


def resolve_s3_location(location=None, *, server_address: str | None = None,
                         bucket: str | None = None, key: str | None = None,
                         secure: bool = True) -> S3Location:
    """Shared argument-resolution for open_s3()/save_s3(): accepts either an
    explicit `location` (an S3Location, or a combined virtual-hosted-style
    URL string, parsed automatically) or the three fields given separately."""
    if location is not None:
        if isinstance(location, S3Location):
            return location
        if isinstance(location, str):
            return S3Location.from_url(location)
        raise TypeError(f"location must be an S3Location or a URL string, got {type(location)!r}")
    if server_address is None or bucket is None or key is None:
        raise ValueError(
            "provide either `location` (an S3Location, or a combined "
            "https://<bucket>.s3.<server_address>/<key> URL string) or all three of "
            "server_address=, bucket=, key="
        )
    return S3Location(server_address=server_address, bucket=bucket, key=key, secure=secure)
