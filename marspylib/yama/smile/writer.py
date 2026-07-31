"""Streaming Smile binary writer, matching Jackson's SmileGenerator output
exactly for the feature set Mars uses: header written, shared field names
on, shared string values off, binary 7-bit encoded, no end marker.
"""

from __future__ import annotations

import struct
from typing import BinaryIO

from . import constants as C
from .binary7 import encode_7bit
from .shared_names import SharedNameTable
from .vint import write_positive_vint, zigzag_encode


class SmileWriter:
    def __init__(self, stream: BinaryIO):
        self._stream = stream
        self._names = SharedNameTable()

    def write_header(self) -> None:
        flags = C.HEADER_BIT_HAS_SHARED_NAMES
        self._stream.write(bytes([C.HEADER_BYTE_1, C.HEADER_BYTE_2, C.HEADER_BYTE_3,
                                   C.HEADER_BYTE_4 | flags]))

    def write_start_object(self) -> None:
        self._stream.write(bytes([C.TOKEN_LITERAL_START_OBJECT]))

    def write_end_object(self) -> None:
        self._stream.write(bytes([C.TOKEN_LITERAL_END_OBJECT]))

    def write_start_array(self) -> None:
        self._stream.write(bytes([C.TOKEN_LITERAL_START_ARRAY]))

    def write_end_array(self) -> None:
        self._stream.write(bytes([C.TOKEN_LITERAL_END_ARRAY]))

    def write_field_name(self, name: str) -> None:
        if name == "":
            self._stream.write(bytes([C.TOKEN_KEY_EMPTY_STRING]))
            return
        ix = self._names.index_of(name)
        if ix is not None:
            self._write_shared_key_ref(ix)
            return
        utf8 = name.encode("utf-8")
        byte_len = len(utf8)
        is_ascii = byte_len == len(name)
        if is_ascii and byte_len <= C.MAX_SHORT_NAME_ASCII_BYTES:
            token = (C.TOKEN_PREFIX_KEY_ASCII - 1) + byte_len
            self._stream.write(bytes([token]) + utf8)
        elif (not is_ascii) and byte_len <= C.MAX_SHORT_NAME_UNICODE_BYTES:
            token = (C.TOKEN_PREFIX_KEY_UNICODE - 2) + byte_len
            self._stream.write(bytes([token]) + utf8)
        else:
            self._stream.write(bytes([C.TOKEN_KEY_LONG_STRING]) + utf8 +
                                bytes([C.BYTE_MARKER_END_OF_STRING]))
        self._names.add(name)

    def _write_shared_key_ref(self, ix: int) -> None:
        if ix < 64:
            self._stream.write(bytes([C.TOKEN_PREFIX_KEY_SHARED_SHORT + ix]))
        else:
            self._stream.write(bytes([C.TOKEN_PREFIX_KEY_SHARED_LONG + (ix >> 8), ix & 0xFF]))

    def write_string(self, value: str | None) -> None:
        if value is None:
            self.write_null()
            return
        if value == "":
            self._stream.write(bytes([C.TOKEN_LITERAL_EMPTY_STRING]))
            return
        utf8 = value.encode("utf-8")
        byte_len = len(utf8)
        is_ascii = byte_len == len(value)
        if byte_len <= C.MAX_SHORT_VALUE_STRING_BYTES:
            if is_ascii:
                token = (C.TOKEN_PREFIX_TINY_ASCII - 1) + byte_len
            else:
                token = (C.TOKEN_PREFIX_TINY_UNICODE - 2) + byte_len
            self._stream.write(bytes([token]) + utf8)
        else:
            token = C.TOKEN_MISC_LONG_TEXT_ASCII if is_ascii else C.TOKEN_MISC_LONG_TEXT_UNICODE
            self._stream.write(bytes([token]) + utf8 + bytes([C.BYTE_MARKER_END_OF_STRING]))

    def write_int(self, value: int) -> None:
        zz = zigzag_encode(value)
        if 0 <= zz <= 31:
            self._stream.write(bytes([C.TOKEN_PREFIX_SMALL_INT + zz]))
        else:
            self._stream.write(bytes([C.TOKEN_BYTE_INT_32]) + write_positive_vint(zz))

    def write_number(self, value: float) -> None:
        """Always emits the float64 (0x29) token -- the only numeric type Mars uses for doubles."""
        l = struct.unpack(">Q", struct.pack(">d", value))[0]
        hi5 = l >> 35
        b4 = hi5 & 0x7F; hi5 >>= 7
        b3 = hi5 & 0x7F; hi5 >>= 7
        b2 = hi5 & 0x7F; hi5 >>= 7
        b1 = hi5 & 0x7F; hi5 >>= 7
        b0 = hi5 & 0x7F
        mid = (l >> 28) & 0x7F
        lo4 = l & 0xFFFFFFFF
        b9 = lo4 & 0x7F; lo4 >>= 7
        b8 = lo4 & 0x7F; lo4 >>= 7
        b7 = lo4 & 0x7F; lo4 >>= 7
        b6 = lo4 & 0x7F
        self._stream.write(bytes([C.TOKEN_BYTE_FLOAT_64, b0, b1, b2, b3, b4, mid, b6, b7, b8, b9]))

    def write_bool(self, value: bool) -> None:
        self._stream.write(bytes([C.TOKEN_LITERAL_TRUE if value else C.TOKEN_LITERAL_FALSE]))

    def write_null(self) -> None:
        self._stream.write(bytes([C.TOKEN_LITERAL_NULL]))

    def write_binary(self, data: bytes) -> None:
        self._stream.write(bytes([C.TOKEN_MISC_BINARY_7BIT]))
        self._stream.write(write_positive_vint(len(data)))
        self._stream.write(encode_7bit(data))

    def close(self) -> None:
        # No end marker (WRITE_END_MARKER=false) and no internal buffering to flush.
        pass


def write_generic_value(writer: SmileWriter, value) -> None:
    """Mirror of smile.reader.read_generic_value: encode plain Python
    dict/list/str/float/int/bool/None trees, for schema-opaque subtrees."""
    if isinstance(value, dict):
        writer.write_start_object()
        for key, v in value.items():
            writer.write_field_name(key)
            write_generic_value(writer, v)
        writer.write_end_object()
    elif isinstance(value, list):
        writer.write_start_array()
        for v in value:
            write_generic_value(writer, v)
        writer.write_end_array()
    elif isinstance(value, bool):
        writer.write_bool(value)
    elif isinstance(value, str):
        writer.write_string(value)
    elif isinstance(value, int):
        writer.write_int(value)
    elif isinstance(value, float):
        writer.write_number(value)
    elif value is None:
        writer.write_null()
    elif isinstance(value, (bytes, bytearray)):
        writer.write_binary(bytes(value))
    else:
        raise TypeError(f"cannot encode value of type {type(value)!r} as generic Smile value")
