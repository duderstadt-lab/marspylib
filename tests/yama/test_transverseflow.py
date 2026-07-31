import tempfile
from pathlib import Path

import marspylib.yama as yama
from marspylib.yama.model import TransverseFlowMolecule

FIXTURE = Path(__file__).parent / "fixtures" / "yama" / "transverseflow_archive.yama"


def test_open_transverseflow_archive():
    archive = yama.open(FIXTURE)
    assert archive.properties.archive_type == "de.mpg.biochem.mars.transverseflow.TransverseFlowArchive"
    assert len(archive) == 2
    assert "tf1" in archive and "tf2" in archive


def test_replication_fork_shape():
    archive = yama.open(FIXTURE)
    mol1 = archive["tf1"]
    assert isinstance(mol1, TransverseFlowMolecule)
    assert mol1.tags == ["fork"]
    assert mol1.metadata_uid == "tfmeta1"

    shape = mol1.replication_fork_shapes[3]
    assert shape.parental_x == [0.0, 1.0, 2.0]
    assert shape.parental_y == [0.0, 0.1, 0.2]
    assert shape.leading_x == [2.0, 3.0, 4.0]
    assert shape.leading_y == [0.2, 0.3, 0.4]
    assert shape.lagging_x == [2.0, 3.0, 4.0]
    assert shape.lagging_y == [0.2, -0.3, -0.4]
    assert shape.parental_intensity == {"GFP": {0: 1.5, 1: 2.5}}
    assert shape.leading_intensity == {"RFP": {0: 3.5}}
    assert shape.lagging_intensity == {"GFP": {2: 9.9}}


def test_no_shapes():
    archive = yama.open(FIXTURE)
    mol2 = archive["tf2"]
    assert isinstance(mol2, TransverseFlowMolecule)
    assert mol2.replication_fork_shapes == {}


def test_write_read_roundtrip():
    archive = yama.open(FIXTURE)
    shape = yama.ReplicationForkShape(
        parental_x=[10.0, 11.0], parental_y=[12.0, 13.0],
        leading_x=[14.0, 15.0], leading_y=[16.0, 17.0],
        lagging_x=[18.0, 19.0], lagging_y=[20.0, 21.0],
        lagging_intensity={"Cy5": {7: 42.5}},
    )
    archive["tf2"].replication_fork_shapes[7] = shape

    with tempfile.TemporaryDirectory() as tmp:
        out_path = Path(tmp) / "roundtrip.yama"
        archive.save(out_path)
        reopened = yama.open(out_path)

    reopened_shape = reopened["tf2"].replication_fork_shapes[7]
    assert reopened_shape.lagging_x == [18.0, 19.0]
    assert reopened_shape.lagging_intensity == {"Cy5": {7: 42.5}}
    # confirm the original tf1 record is untouched by the round-trip
    assert reopened["tf1"].replication_fork_shapes[3].parental_x == [0.0, 1.0, 2.0]
