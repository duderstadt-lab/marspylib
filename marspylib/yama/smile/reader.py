"""Streaming Smile binary reader, matching Jackson's SmileParser token
dispatch exactly. Key (field-name) tokens and value tokens use disjoint byte
ranges with different meanings, so they are decoded by two separate
functions -- never a shared lookup table -- mirroring
SmileParser._handleFieldName vs SmileParser.nextToken's value-mode switch.
"""

from __future__ import annotations

import enum
import struct

from . import constants as C
from .binary7 import decode_7bit, encoded_length
from .shared_names import SharedNameTable
from .vint import read_positive_vint, zigzag_decode
from ..errors import SmileFormatError


class SmileToken(enum.Enum):
    START_OBJECT = "START_OBJECT"
    END_OBJECT = "END_OBJECT"
    START_ARRAY = "START_ARRAY"
    END_ARRAY = "END_ARRAY"
    FIELD_NAME = "FIELD_NAME"
    VALUE_STRING = "VALUE_STRING"
    VALUE_INT = "VALUE_INT"
    VALUE_DOUBLE = "VALUE_DOUBLE"
    VALUE_TRUE = "VALUE_TRUE"
    VALUE_FALSE = "VALUE_FALSE"
    VALUE_NULL = "VALUE_NULL"
    VALUE_BINARY = "VALUE_BINARY"
    END_OF_INPUT = "END_OF_INPUT"


_SCALAR_VALUE_TOKENS = {
    SmileToken.VALUE_STRING, SmileToken.VALUE_INT, SmileToken.VALUE_DOUBLE,
    SmileToken.VALUE_TRUE, SmileToken.VALUE_FALSE, SmileToken.VALUE_NULL,
    SmileToken.VALUE_BINARY,
}


class SmileReader:
    def __init__(self, data: bytes):
        self._data = data
        self._pos = 0
        self._names = SharedNameTable()
        self._string_values: SharedNameTable | None = None
        self._context_stack: list[str] = []
        self._current_token: SmileToken | None = None
        self._current_name: str | None = None
        self._current_text: str | None = None
        self._current_int: int | None = None
        self._current_double: float | None = None
        self._current_binary: bytes | None = None
        self._read_header()

    def _read_header(self) -> None:
        data = self._data
        if (len(data) < 4 or data[0] != C.HEADER_BYTE_1 or data[1] != C.HEADER_BYTE_2
                or data[2] != C.HEADER_BYTE_3):
            raise SmileFormatError("missing or invalid Smile header")
        flags = data[3] & 0x0F
        if flags & C.HEADER_BIT_HAS_SHARED_STRING_VALUES:
            self._string_values = SharedNameTable()
        self._pos = 4

    # -- public token-cursor API -------------------------------------------------

    def next_token(self) -> SmileToken:
        if self._current_token != SmileToken.FIELD_NAME and self._in_object():
            tok = self._read_key_token()
        else:
            tok = self._read_value_token()
        self._current_token = tok
        return tok

    def current_name(self) -> str:
        return self._current_name

    def get_text(self) -> str:
        return self._current_text

    def get_int(self) -> int:
        return self._current_int

    def get_double(self) -> float:
        return self._current_double

    def get_binary(self) -> bytes:
        return self._current_binary

    def skip_value(self) -> None:
        """Skip the subtree started by the just-returned token (no-op for scalars)."""
        if self._current_token not in (SmileToken.START_OBJECT, SmileToken.START_ARRAY):
            return
        depth = 1
        while depth > 0:
            tok = self.next_token()
            if tok in (SmileToken.START_OBJECT, SmileToken.START_ARRAY):
                depth += 1
            elif tok in (SmileToken.END_OBJECT, SmileToken.END_ARRAY):
                depth -= 1
            elif tok == SmileToken.END_OF_INPUT:
                raise SmileFormatError("unexpected end of input while skipping value")

    # -- internal ------------------------------------------------------------

    def _in_object(self) -> bool:
        return bool(self._context_stack) and self._context_stack[-1] == "object"

    def _read_utf8(self, pos: int, byte_len: int) -> tuple[str, int]:
        end = pos + byte_len
        return self._data[pos:end].decode("utf-8"), end

    def _read_terminated_utf8(self, pos: int) -> tuple[str, int]:
        end = self._data.index(C.BYTE_MARKER_END_OF_STRING, pos)
        return self._data[pos:end].decode("utf-8"), end + 1

    def _get_shared_string_value(self, idx: int) -> str:
        if self._string_values is None:
            raise SmileFormatError("shared string value reference but sharing is disabled")
        return self._string_values.get(idx)

    def _read_float64(self) -> float:
        d = self._data
        p = self._pos
        b0, b1, b2, b3, b4, mid, b6, b7, b8, b9 = d[p:p + 10]
        self._pos = p + 10
        hi5 = b0
        for b in (b1, b2, b3, b4):
            hi5 = (hi5 << 7) | b
        lo4 = b6
        for b in (b7, b8, b9):
            lo4 = (lo4 << 7) | b
        l = (hi5 << 35) | (mid << 28) | lo4
        return struct.unpack(">d", struct.pack(">Q", l & 0xFFFFFFFFFFFFFFFF))[0]

    def _read_float32(self) -> float:
        d = self._data
        p = self._pos
        b0, b1, b2, b3, b4 = d[p:p + 5]
        self._pos = p + 5
        i = b0
        for b in (b1, b2, b3, b4):
            i = (i << 7) | b
        return struct.unpack(">f", struct.pack(">I", i & 0xFFFFFFFF))[0]

    def _read_key_token(self) -> SmileToken:
        if self._pos >= len(self._data):
            return SmileToken.END_OF_INPUT
        ch = self._data[self._pos]
        self._pos += 1

        if ch == C.TOKEN_KEY_EMPTY_STRING:
            self._current_name = ""
            return SmileToken.FIELD_NAME

        if C.TOKEN_PREFIX_KEY_SHARED_LONG <= ch <= C.TOKEN_PREFIX_KEY_SHARED_LONG + 3:
            idx = ((ch & 0x3) << 8) | self._data[self._pos]
            self._pos += 1
            self._current_name = self._names.get(idx)
            return SmileToken.FIELD_NAME

        if ch == C.TOKEN_KEY_LONG_STRING:
            name, self._pos = self._read_terminated_utf8(self._pos)
            self._names.add(name)
            self._current_name = name
            return SmileToken.FIELD_NAME

        if C.TOKEN_PREFIX_KEY_SHARED_SHORT <= ch < C.TOKEN_PREFIX_KEY_ASCII:
            idx = ch & 0x3F
            self._current_name = self._names.get(idx)
            return SmileToken.FIELD_NAME

        if C.TOKEN_PREFIX_KEY_ASCII <= ch < C.TOKEN_PREFIX_KEY_UNICODE:
            byte_len = ch - (C.TOKEN_PREFIX_KEY_ASCII - 1)
            name, self._pos = self._read_utf8(self._pos, byte_len)
            self._names.add(name)
            self._current_name = name
            return SmileToken.FIELD_NAME

        if ch == C.TOKEN_LITERAL_END_OBJECT:
            if not self._context_stack or self._context_stack[-1] != "object":
                raise SmileFormatError("END_OBJECT without matching START_OBJECT")
            self._context_stack.pop()
            return SmileToken.END_OBJECT

        if C.TOKEN_PREFIX_KEY_UNICODE <= ch <= 0xF7:
            byte_len = ch - (C.TOKEN_PREFIX_KEY_UNICODE - 2)
            name, self._pos = self._read_utf8(self._pos, byte_len)
            self._names.add(name)
            self._current_name = name
            return SmileToken.FIELD_NAME

        raise SmileFormatError(f"unsupported/reserved key type byte 0x{ch:02x} at offset {self._pos - 1}")

    def _read_value_token(self) -> SmileToken:
        if self._pos >= len(self._data):
            return SmileToken.END_OF_INPUT
        ch = self._data[self._pos]
        self._pos += 1
        top3 = ch >> 5

        if top3 == 0:
            if ch == 0:
                raise SmileFormatError(f"invalid value type byte 0x00 at offset {self._pos - 1}")
            self._current_text = self._get_shared_string_value(ch - 1)
            return SmileToken.VALUE_STRING

        if top3 == 1:
            type_bits = ch & 0x1F
            if type_bits == 0x00:
                self._current_text = ""
                return SmileToken.VALUE_STRING
            if type_bits == 0x01:
                return SmileToken.VALUE_NULL
            if type_bits == 0x02:
                return SmileToken.VALUE_FALSE
            if type_bits == 0x03:
                return SmileToken.VALUE_TRUE
            if type_bits in (0x04, 0x05):  # int32, int64 -- same VInt+zigzag encoding
                zz, self._pos = read_positive_vint(self._data, self._pos)
                self._current_int = zigzag_decode(zz)
                return SmileToken.VALUE_INT
            if type_bits == 0x06:
                raise SmileFormatError("BigInteger values are not supported")
            if type_bits == 0x08:
                self._current_double = self._read_float32()
                return SmileToken.VALUE_DOUBLE
            if type_bits == 0x09:
                self._current_double = self._read_float64()
                return SmileToken.VALUE_DOUBLE
            if type_bits == 0x0A:
                raise SmileFormatError("BigDecimal values are not supported")
            raise SmileFormatError(f"unsupported/reserved value type byte 0x{ch:02x} at offset {self._pos - 1}")

        if top3 in (2, 3, 4, 5):
            if top3 in (2, 3):
                byte_len = ch - (C.TOKEN_PREFIX_TINY_ASCII - 1)
            else:
                byte_len = ch - (C.TOKEN_PREFIX_TINY_UNICODE - 2)
            text, self._pos = self._read_utf8(self._pos, byte_len)
            if self._string_values is not None:
                self._string_values.add(text)
            self._current_text = text
            return SmileToken.VALUE_STRING

        if top3 == 6:
            self._current_int = zigzag_decode(ch & 0x1F)
            return SmileToken.VALUE_INT

        # top3 == 7: 0xE0-0xFF
        low = ch & 0x1F
        if low == 0x00 or low == 0x04:  # long ASCII / long Unicode text
            text, self._pos = self._read_terminated_utf8(self._pos)
            self._current_text = text
            return SmileToken.VALUE_STRING
        if low == 0x08:  # binary, 7-bit
            length, self._pos = read_positive_vint(self._data, self._pos)
            enc_len = encoded_length(length)
            chunk = self._data[self._pos:self._pos + enc_len]
            self._pos += enc_len
            self._current_binary = decode_7bit(chunk, length)
            return SmileToken.VALUE_BINARY
        if 0x0C <= low <= 0x0F:  # long shared string value ref
            idx = ((ch & 0x3) << 8) | self._data[self._pos]
            self._pos += 1
            self._current_text = self._get_shared_string_value(idx)
            return SmileToken.VALUE_STRING
        if low == 0x18:
            self._context_stack.append("array")
            return SmileToken.START_ARRAY
        if low == 0x19:
            if not self._context_stack or self._context_stack[-1] != "array":
                raise SmileFormatError("END_ARRAY without matching START_ARRAY")
            self._context_stack.pop()
            return SmileToken.END_ARRAY
        if low == 0x1A:
            self._context_stack.append("object")
            return SmileToken.START_OBJECT
        if low == 0x1B:
            raise SmileFormatError("unexpected END_OBJECT in value-mode context")
        if low == 0x1D:
            raise SmileFormatError("raw (non-7bit) binary values are not supported")
        if low == 0x1F:
            return SmileToken.END_OF_INPUT
        raise SmileFormatError(f"unsupported/reserved value type byte 0x{ch:02x} at offset {self._pos - 1}")


def read_generic_value(reader: "SmileReader", token: SmileToken):
    """Recursively decode the value at `token` into plain Python objects
    (dict/list/str/float/int/bool/None) -- used for schema-opaque subtrees."""
    if token == SmileToken.START_OBJECT:
        obj = {}
        while True:
            tok = reader.next_token()
            if tok == SmileToken.END_OBJECT:
                return obj
            if tok != SmileToken.FIELD_NAME:
                raise SmileFormatError(f"expected FIELD_NAME or END_OBJECT, got {tok}")
            name = reader.current_name()
            obj[name] = read_generic_value(reader, reader.next_token())
        return obj
    if token == SmileToken.START_ARRAY:
        items = []
        while True:
            tok = reader.next_token()
            if tok == SmileToken.END_ARRAY:
                return items
            items.append(read_generic_value(reader, tok))
    if token == SmileToken.VALUE_STRING:
        return reader.get_text()
    if token == SmileToken.VALUE_INT:
        return reader.get_int()
    if token == SmileToken.VALUE_DOUBLE:
        return reader.get_double()
    if token == SmileToken.VALUE_TRUE:
        return True
    if token == SmileToken.VALUE_FALSE:
        return False
    if token == SmileToken.VALUE_NULL:
        return None
    if token == SmileToken.VALUE_BINARY:
        return reader.get_binary()
    raise SmileFormatError(f"unexpected token {token} while decoding generic value")
