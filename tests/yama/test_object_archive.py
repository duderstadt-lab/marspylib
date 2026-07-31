import tempfile
from pathlib import Path

import marspylib.yama as yama
from marspylib.yama.model import MartianObject

FIXTURE = Path(__file__).parent / "fixtures" / "yama" / "object_archive.yama"


def test_open_object_archive():
    archive = yama.open(FIXTURE)
    assert archive.properties.archive_type == "de.mpg.biochem.mars.object.ObjectArchive"
    assert len(archive) == 2
    assert "obj1" in archive and "obj2" in archive


def test_martian_object_shapes():
    archive = yama.open(FIXTURE)
    obj1 = archive["obj1"]
    assert isinstance(obj1, MartianObject)
    assert obj1.tags == ["tracked"]
    assert obj1.metadata_uid == "ometa1"
    assert set(obj1.shapes) == {0, 1}
    assert obj1.shapes[0].x == [0.0, 1.0, 1.0, 0.0]
    assert obj1.shapes[0].y == [0.0, 0.0, 1.0, 1.0]
    assert obj1.shapes[1].x == [0.5, 1.5, 1.5, 0.5, 0.2]


def test_martian_object_no_shapes():
    archive = yama.open(FIXTURE)
    obj2 = archive["obj2"]
    assert isinstance(obj2, MartianObject)
    assert obj2.shapes == {}


def test_write_read_roundtrip():
    archive = yama.open(FIXTURE)
    archive["obj2"].shapes[9] = yama.PeakShape(x=[7.0, 8.0], y=[9.0, 10.0])
    with tempfile.TemporaryDirectory() as tmp:
        out_path = Path(tmp) / "roundtrip.yama"
        archive.save(out_path)
        reopened = yama.open(out_path)

    assert reopened.properties.archive_type == "de.mpg.biochem.mars.object.ObjectArchive"
    obj1 = reopened["obj1"]
    assert obj1.shapes[0].x == [0.0, 1.0, 1.0, 0.0]
    obj2 = reopened["obj2"]
    assert obj2.shapes[9].x == [7.0, 8.0] and obj2.shapes[9].y == [9.0, 10.0]
