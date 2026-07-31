"""Byte-level constants transcribed from jackson-dataformat-smile 2.18.0
(com.fasterxml.jackson.dataformat.smile.SmileConstants /
com.fasterxml.jackson.dataformat.smile.SmileGenerator), verified directly
against the library sources rather than derived from prose. Field names and
comments intentionally mirror the Java source so the two can be diffed by eye.
"""

# --- header ---
HEADER_BYTE_1 = 0x3A  # ':'
HEADER_BYTE_2 = 0x29  # ')'
HEADER_BYTE_3 = 0x0A  # '\n'
HEADER_VERSION_0 = 0x0
HEADER_BYTE_4 = HEADER_VERSION_0 << 4

HEADER_BIT_HAS_SHARED_NAMES = 0x01
HEADER_BIT_HAS_SHARED_STRING_VALUES = 0x02
HEADER_BIT_HAS_RAW_BINARY = 0x04

# --- structural / literal tokens (value mode) ---
TOKEN_LITERAL_EMPTY_STRING = 0x20
TOKEN_LITERAL_NULL = 0x21
TOKEN_LITERAL_FALSE = 0x22
TOKEN_LITERAL_TRUE = 0x23

TOKEN_LITERAL_START_ARRAY = 0xF8
TOKEN_LITERAL_END_ARRAY = 0xF9
TOKEN_LITERAL_START_OBJECT = 0xFA
TOKEN_LITERAL_END_OBJECT = 0xFB

# --- numeric tokens (value mode) ---
TOKEN_PREFIX_INTEGER = 0x24  # + 0x00 = int32, + 0x01 = int64, + 0x02 = bigint
TOKEN_BYTE_INT_32 = 0x24
TOKEN_BYTE_INT_64 = 0x25
TOKEN_BYTE_INT_BIG = 0x26

TOKEN_PREFIX_FP = 0x28  # + 0x00 = float32, + 0x01 = float64, + 0x02 = bigdecimal
TOKEN_BYTE_FLOAT_32 = 0x28
TOKEN_BYTE_FLOAT_64 = 0x29
TOKEN_BYTE_BIG_DECIMAL = 0x2A

TOKEN_PREFIX_SMALL_INT = 0xC0  # + zigzag(value), value in [0, 31] -> 0xC0-0xDF

# --- string value tokens (value mode) ---
TOKEN_PREFIX_SHARED_STRING_SHORT = 0x00  # byte = 1 + index, index in [0, 30]
TOKEN_PREFIX_TINY_ASCII = 0x40  # byte = 0x3F + byteLen, byteLen in [1, 64]
TOKEN_PREFIX_TINY_UNICODE = 0x80  # byte = 0x7E + byteLen, byteLen in [2, 64]
TOKEN_MISC_LONG_TEXT_ASCII = 0xE0
TOKEN_MISC_LONG_TEXT_UNICODE = 0xE4
TOKEN_PREFIX_SHARED_STRING_LONG = 0xEC  # + (index >> 8); low byte follows

TOKEN_MISC_BINARY_7BIT = 0xE8
TOKEN_MISC_BINARY_RAW = 0xFD

MAX_SHORT_VALUE_STRING_BYTES = 64
MAX_SHARED_STRING_LENGTH_BYTES = 65  # strings longer than this are never shared

BYTE_MARKER_END_OF_STRING = 0xFC

# --- field name (key) tokens (key mode) ---
TOKEN_KEY_EMPTY_STRING = 0x20
TOKEN_PREFIX_KEY_SHARED_LONG = 0x30  # ch in 0x30-0x33; index = ((ch&0x3)<<8)+next
TOKEN_KEY_LONG_STRING = 0x34
TOKEN_PREFIX_KEY_SHARED_SHORT = 0x40  # ch in 0x40-0x7F; index = ch & 0x3F
TOKEN_PREFIX_KEY_ASCII = 0x80  # byte = 0x7F + byteLen, byteLen in [1, 64] -> 0x80-0xBF
TOKEN_PREFIX_KEY_UNICODE = 0xC0  # byte = 0xBE + byteLen, byteLen in [2, 56] -> 0xC0-0xF6

MAX_SHORT_NAME_ASCII_BYTES = 64
MAX_SHORT_NAME_UNICODE_BYTES = 56
MAX_SHORT_NAME_ANY_BYTES = 64

MAX_SHARED_NAMES = 1024
MAX_SHARED_STRING_VALUES = 1024
