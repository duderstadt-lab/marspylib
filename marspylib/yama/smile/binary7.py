"""Smile's 7-bit-safe binary encoding: every 7 input bytes (56 bits) become
8 output bytes, each holding 7 bits with the top bit always clear.

Derived from com.fasterxml.jackson.dataformat.smile.SmileGenerator
._write7BitBinaryWithLength (encode) and SmileParser._read7BitBinaryWithLength
(decode), and verified to unify to one rule for both full 7-byte groups and
the trailing partial group (1-6 bytes): a group of ``n`` original bytes
(1 <= n <= 7) is packed into ``n + 1`` encoded bytes -- the first ``n`` hold
7 bits each from the top of the group's bit stream, and the final byte holds
the ``n`` remaining low bits, right-aligned and *not* padded to 7 bits.
"""


def encode_7bit(data: bytes) -> bytes:
    out = bytearray()
    pos = 0
    total = len(data)
    while pos < total:
        n = min(7, total - pos)
        chunk = data[pos:pos + n]
        pos += n
        value = int.from_bytes(chunk, "big")
        bits = 8 * n
        for k in range(n):
            shift = bits - 7 * (k + 1)
            out.append((value >> shift) & 0x7F)
        out.append(value & ((1 << n) - 1))
    return bytes(out)


def decode_7bit(encoded: bytes, length: int) -> bytes:
    """Decode `length` original bytes from `encoded` 7-bit groups."""
    out = bytearray()
    epos = 0
    remaining = length
    while remaining > 0:
        n = min(7, remaining)
        value = 0
        for i in range(n):
            value = (value << 7) | encoded[epos + i]
        value = (value << n) | encoded[epos + n]
        out += value.to_bytes(n, "big")
        epos += n + 1
        remaining -= n
    return bytes(out)


def encoded_length(byte_length: int) -> int:
    """Number of encoded bytes produced by encode_7bit for `byte_length` input bytes."""
    full, rem = divmod(byte_length, 7)
    return full * 8 + (rem + 1 if rem else 0)
