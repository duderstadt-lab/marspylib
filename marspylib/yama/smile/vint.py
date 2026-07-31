"""Zigzag and positive-VInt encoding, transcribed from
com.fasterxml.jackson.dataformat.smile.SmileUtil (zigzag) and
SmileGenerator._writePositiveVInt / SmileParser._readUnsignedVInt.

A positive VInt packs a non-negative integer into 1-5 bytes: every byte but
the last carries 7 bits (top bit clear), the last byte carries only 6 bits
and has its top bit *set* (0x80 | low6bits) to mark the end of the value.
"""

from __future__ import annotations


def zigzag_encode(value: int) -> int:
    """Map a signed int to an unsigned value, small magnitudes first.

    Equivalent to Java's ``(n << 1) ^ (n >> 31)`` for the int32 range Mars
    actually uses, expressed as the canonical direct formula so it isn't
    tied to a fixed bit width.
    """
    return value * 2 if value >= 0 else (-value * 2) - 1


def zigzag_decode(encoded: int) -> int:
    if encoded % 2 == 0:
        return encoded // 2
    return -(encoded + 1) // 2


def write_positive_vint(value: int) -> bytes:
    if value < 0:
        raise ValueError(f"positive VInt cannot encode negative value {value}")
    groups = [value & 0x3F]
    value >>= 6
    while value > 0:
        groups.append(value & 0x7F)
        value >>= 7
    # groups[0] holds the terminal (least-significant) 6 bits; the rest hold
    # 7 bits each and are written most-significant-group first.
    out = bytearray()
    for group in reversed(groups[1:]):
        out.append(group)
    out.append(0x80 | groups[0])
    return bytes(out)


def read_positive_vint(data: bytes, pos: int) -> tuple[int, int]:
    """Return (value, new_pos) reading a positive VInt starting at data[pos]."""
    value = 0
    while True:
        b = data[pos]
        pos += 1
        if b & 0x80:
            value = (value << 6) | (b & 0x3F)
            return value, pos
        value = (value << 7) | b


def write_signed_vint(value: int) -> bytes:
    return write_positive_vint(zigzag_encode(value))


def read_signed_vint(data: bytes, pos: int) -> tuple[int, int]:
    zz, pos = read_positive_vint(data, pos)
    return zigzag_decode(zz), pos
