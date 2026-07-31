import math
from pathlib import Path

from marspylib.yama.smile.reader import SmileReader
from marspylib.yama.io.table import read_table

FIXTURES = Path(__file__).parent / "fixtures" / "table"


def test_mars_table_mixed_columns():
    data = (FIXTURES / "mars_table.bin").read_bytes()
    reader = SmileReader(data)
    reader.next_token()
    df = read_table(reader)

    assert list(df.columns) == ["T", "x", "label"]
    assert len(df) == 20
    assert df["T"].tolist() == [float(i) for i in range(20)]
    assert math.isnan(df["x"][5])
    for i in range(20):
        if i != 5:
            assert abs(df["x"][i] - math.sin(i) * 100.0) < 1e-9
    assert df["label"].tolist() == [f"row{i}" for i in range(20)]


def test_mars_table_empty():
    data = (FIXTURES / "mars_table_empty.bin").read_bytes()
    reader = SmileReader(data)
    reader.next_token()
    df = read_table(reader)
    assert df.empty
    assert len(df.columns) == 0
