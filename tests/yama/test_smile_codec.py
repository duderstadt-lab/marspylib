import io
import math
from pathlib import Path

import pytest

from marspylib.yama.smile.reader import SmileReader, read_generic_value
from marspylib.yama.smile.writer import SmileWriter, write_generic_value

FIXTURES = Path(__file__).parent / "fixtures" / "smile"


def _decode_fixture(name):
    data = (FIXTURES / f"{name}.bin").read_bytes()
    reader = SmileReader(data)
    return read_generic_value(reader, reader.next_token())


def _roundtrip(value):
    buf = io.BytesIO()
    writer = SmileWriter(buf)
    writer.write_header()
    write_generic_value(writer, value)
    writer.close()
    data = buf.getvalue()
    reader = SmileReader(data)
    return read_generic_value(reader, reader.next_token()), data


# -- decode real Jackson-written fixtures ------------------------------------

def test_decode_basic_mixed():
    assert _decode_fixture("basic_mixed") == {
        "a": "hello", "b": 1, "c": 3.14159, "d": True, "e": False, "f": None,
    }


def test_decode_shared_names_repeat():
    value = _decode_fixture("shared_names_repeat")
    assert len(value) == 50
    assert value[0] == {"uid": "id0", "tags": ["a", "b"], "notes": "n"}
    assert value[49] == {"uid": "id49", "tags": ["a", "b"], "notes": "n"}


def test_decode_shared_names_wraparound():
    value = _decode_fixture("shared_names_wraparound")
    assert len(value) == 1100
    for i in (0, 500, 1023, 1024, 1025, 1099):
        assert value[f"field_{i}"] == i


def test_decode_numbers_all_types():
    value = _decode_fixture("numbers_all_types")
    ints = [0, 1, -1, 31, -31, 32, -32, 63, 64, 1000000, -1000000, 2**31 - 1, -(2**31)]
    assert value[:len(ints)] == ints
    doubles = value[len(ints):]
    expected = [0.0, -0.0, 1.0, -1.5, 3.14159265358979, float("inf"), float("-inf"),
                None, 5e-324, 1.7976931348623157e308]
    for got, exp in zip(doubles, expected):
        if exp is None:
            assert math.isnan(got)
        else:
            assert got == exp
            assert math.copysign(1, got) == math.copysign(1, exp)


def test_decode_strings_all_kinds():
    assert _decode_fixture("strings_all_kinds") == [
        "", "a", "ab" * 40, "unicode: éè中文", "x" * 200, "é" * 100,
    ]


def test_decode_long_field_name():
    assert _decode_fixture("long_field_name") == {"k" * 100: "v"}


def test_decode_binary_blob():
    value = _decode_fixture("binary_blob")
    assert value["small"] == bytes((i * 17 + 1) & 0xFF for i in range(3))
    assert value["exact7"] == bytes((i * 31 + 3) & 0xFF for i in range(7))
    assert value["multi"] == bytes((i * 37 + 5) % 256 for i in range(100))


def test_decode_nested_empty():
    assert _decode_fixture("nested_empty") == {"emptyArray": [], "emptyObject": {}}


# -- writer output is byte-identical to Jackson's for the same content -------

@pytest.mark.parametrize("name,value", [
    ("basic_mixed", {"a": "hello", "b": 1, "c": 3.14159, "d": True, "e": False, "f": None}),
    ("shared_names_repeat",
     [{"uid": f"id{i}", "tags": ["a", "b"], "notes": "n"} for i in range(50)]),
    ("shared_names_wraparound", {f"field_{i}": i for i in range(1100)}),
    ("strings_all_kinds", ["", "a", "ab" * 40, "unicode: éè中文", "x" * 200, "é" * 100]),
    ("long_field_name", {"k" * 100: "v"}),
    ("nested_empty", {"emptyArray": [], "emptyObject": {}}),
])
def test_writer_byte_identical_to_jackson(name, value):
    _, data = _roundtrip(value)
    assert data == (FIXTURES / f"{name}.bin").read_bytes()


def test_writer_numbers_byte_identical_to_jackson():
    buf = io.BytesIO()
    writer = SmileWriter(buf)
    writer.write_header()
    writer.write_start_array()
    for i in [0, 1, -1, 31, -31, 32, -32, 63, 64, 1000000, -1000000, 2**31 - 1, -(2**31)]:
        writer.write_int(i)
    for d in [0.0, -0.0, 1.0, -1.5, 3.14159265358979, float("inf"), float("-inf"),
              float("nan"), 5e-324, 1.7976931348623157e308]:
        writer.write_number(d)
    writer.write_end_array()
    writer.close()
    assert buf.getvalue() == (FIXTURES / "numbers_all_types.bin").read_bytes()


def test_writer_binary_byte_identical_to_jackson():
    buf = io.BytesIO()
    writer = SmileWriter(buf)
    writer.write_header()
    writer.write_start_object()
    writer.write_field_name("small")
    writer.write_binary(bytes((i * 17 + 1) & 0xFF for i in range(3)))
    writer.write_field_name("exact7")
    writer.write_binary(bytes((i * 31 + 3) & 0xFF for i in range(7)))
    writer.write_field_name("multi")
    writer.write_binary(bytes((i * 37 + 5) % 256 for i in range(100)))
    writer.write_end_object()
    writer.close()
    assert buf.getvalue() == (FIXTURES / "binary_blob.bin").read_bytes()


# -- self-consistency round-trips (no Java oracle needed) --------------------

@pytest.mark.parametrize("value", [
    {}, [],
    {"nested": {"x": [1, 2, 3], "y": {"z": "deep"}}},
    [1, -1, 0, 31, 32, 63, 64, 1000000, -1000000],
    {"binary": b"hello world, this is a longer binary blob" * 3},
])
def test_self_consistency_roundtrip(value):
    got, _ = _roundtrip(value)
    assert got == value


def test_self_consistency_nan_inf_signed_zero():
    got, _ = _roundtrip([float("nan"), float("inf"), float("-inf"), 0.0, -0.0])
    assert math.isnan(got[0])
    assert got[1] == float("inf")
    assert got[2] == float("-inf")
    assert math.copysign(1, got[3]) == 1.0
    assert math.copysign(1, got[4]) == -1.0


def test_self_consistency_fuzz():
    import random
    random.seed(1)

    def rand_val(depth=0):
        if depth > 3:
            return random.choice([1, "x", 1.5, True, None])
        choice = random.randint(0, 6)
        if choice == 0:
            return random.randint(-10**7, 10**7)
        if choice == 1:
            return "".join(random.choice("abcxyzé中 ") for _ in range(random.randint(0, 50)))
        if choice == 2:
            return random.random() * 1000 - 500
        if choice == 3:
            return random.choice([True, False])
        if choice == 4:
            return None
        if choice == 5:
            return [rand_val(depth + 1) for _ in range(random.randint(0, 5))]
        return {f"k{i}": rand_val(depth + 1) for i in range(random.randint(0, 5))}

    for _ in range(200):
        value = rand_val()
        got, _ = _roundtrip(value)
        assert got == value
