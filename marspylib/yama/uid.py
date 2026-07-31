"""UID generation matching mars-core's MarsMath.getUUID58()
(util/MarsMath.java), which uses com.chrylis:base58-codec's Base58UUID: a
random UUID's 16 bytes, Base58-encoded with the standard Bitcoin alphabet
(0/O/I/l excluded, to avoid visually confusing characters).

Verified byte-for-byte against the real com.chrylis:base58-codec library
(disassembled, since no network access was available to fetch its source),
including a real quirk worth knowing rather than "fixing": unlike canonical
Base58Check, this library does not pad for leading zero bytes, so a UUID
that happens to start with one or more zero bytes encodes to a *shorter*
string than usual (about 1-in-256 UUIDs) rather than a same-length,
zero-padded one. This is the actual Java library's behavior.
"""

from __future__ import annotations

import uuid as _uuid

_ALPHABET = "123456789abcdefghijkmnopqrstuvwxyzABCDEFGHJKLMNPQRSTUVWXYZ"
_BASE = len(_ALPHABET)

# Molecule UIDs use the full encoding (AbstractMolecule.java:96,
# `super(MarsMath.getUUID58())`); metadata UIDs use a fixed 10-character
# prefix of the same encoding (AbstractMarsMetadata.java:101,
# `super(MarsMath.getUUID58().substring(0, 10))`) -- a fixed constant in the
# Java source, not literally half of the (variable-length) molecule UID.
METADATA_UID_LENGTH = 10


def _base58_encode(data: bytes) -> str:
    if not data:
        return ""
    value = int.from_bytes(data, "big")
    if value == 0:
        return _ALPHABET[0]
    digits = []
    while value > 0:
        value, remainder = divmod(value, _BASE)
        digits.append(_ALPHABET[remainder])
    return "".join(reversed(digits))


def new_molecule_uid() -> str:
    """A fresh UID in the same format mars-core generates for new molecules."""
    return _base58_encode(_uuid.uuid4().bytes)


def new_metadata_uid() -> str:
    """A fresh UID in the same format mars-core generates for new metadata
    records -- the same encoding as new_molecule_uid(), truncated to
    METADATA_UID_LENGTH characters."""
    return new_molecule_uid()[:METADATA_UID_LENGTH]
