import math
import tempfile
from pathlib import Path

import pandas as pd
import pytest

import marspylib.yama as yama

FIXTURES = Path(__file__).parent / "fixtures" / "yama"


def test_single_molecule_archive():
    archive = yama.open(FIXTURES / "single_molecule_archive.yama")

    assert archive.properties.archive_type == "de.mpg.biochem.mars.molecule.SingleMoleculeArchive"
    assert archive.properties.schema == "2022-04-11"
    assert archive.properties.number_of_molecules == 2
    assert len(archive) == 2
    assert "mol1" in archive and "mol2" in archive

    mol1 = archive["mol1"]
    assert mol1.tags == ["accepted"]
    assert mol1.notes == "test notes"
    assert mol1.channel == 1
    assert mol1.image == 0
    assert mol1.metadata_uid == "meta1"
    assert mol1.parameters["dwell"] == 5.5
    assert mol1.parameters["label"] == "high"
    assert mol1.parameters["flag"] is True
    assert math.isnan(mol1.parameters["nan_val"])
    assert mol1.parameters["inf_val"] == float("inf")
    assert list(mol1.table.columns) == ["T", "Intensity", "label"]
    assert mol1.table["label"].tolist() == [f"f{i}" for i in range(10)]
    assert math.isnan(mol1.table["Intensity"][3])

    region = mol1.regions["r1"]
    assert region.column == "T" and region.start == 1.0 and region.end == 5.0
    assert region.color == "#ff0000ff" and abs(region.opacity - 0.3) < 1e-9

    position = mol1.positions["p1"]
    assert position.column == "T" and position.position == 2.0
    assert position.color == "#00ff00ff" and position.stroke == 3.5

    mol2 = archive["mol2"]
    assert mol2.tags == [] and mol2.parameters == {}
    assert len(mol2.table.columns) == 0

    metas = list(archive.metadata)
    assert len(metas) == 1
    meta = metas[0]
    assert meta.uid == "meta1"
    assert meta.microscope == "TestScope"
    assert meta.source_directory == "/data/exp1"
    assert meta.tags == ["imported"]
    assert archive.metadata_has_tag("meta1", "imported")
    assert not archive.metadata_has_tag("meta1", "nope")

    props = archive.properties
    assert props.tag_set == {"accepted"}
    assert props.channel_set == {1}
    assert props.table_column_set == {"T", "Intensity", "label"}
    assert props.parameter_set == {"dwell", "label", "flag", "nan_val", "inf_val"}
    assert props.region_set == {"r1"}
    assert props.position_set == {"p1"}


def test_dna_molecule_archive():
    archive = yama.open(FIXTURES / "dna_molecule_archive.yama")
    assert archive.properties.archive_type == "de.mpg.biochem.mars.molecule.DnaMoleculeArchive"
    assert len(archive) == 1
    assert archive["dmol1"].metadata_uid == "dmeta1"


def test_default_molecule_archive():
    archive = yama.open(FIXTURES / "default_molecule_archive.yama")
    assert archive.properties.archive_type == "de.mpg.biochem.mars.molecule.DefaultMoleculeArchive"
    assert len(archive) == 1
    assert archive["xmol1"].metadata_uid == "xmeta1"


def test_empty_archive():
    archive = yama.open(FIXTURES / "empty_archive.yama")
    assert len(archive) == 0
    assert list(archive.metadata) == []
    assert archive.properties.number_of_molecules == 0


@pytest.mark.parametrize("name", [
    "single_molecule_archive.yama",
    "dna_molecule_archive.yama",
    "default_molecule_archive.yama",
    "empty_archive.yama",
])
def test_write_read_roundtrip(name):
    """Open a real mars-core fixture, save it back out, and confirm the
    object model survives the round-trip (semantic equality, not byte
    equality -- see the plan's acceptance bar)."""
    archive = yama.open(FIXTURES / name)
    with tempfile.TemporaryDirectory() as tmp:
        out_path = Path(tmp) / "roundtrip.yama"
        archive.save(out_path)
        reopened = yama.open(out_path)

    assert reopened.properties.archive_type == archive.properties.archive_type
    assert reopened.properties.number_of_molecules == archive.properties.number_of_molecules
    assert len(reopened) == len(archive)
    for uid, molecule in archive._molecules.items():
        other = reopened[uid]
        assert other.tags == molecule.tags
        assert other.notes == molecule.notes
        assert other.metadata_uid == molecule.metadata_uid
        pd.testing.assert_frame_equal(other.table, molecule.table, check_exact=False)
        for name_, value in molecule.parameters.items():
            got = other.parameters[name_]
            if isinstance(value, float) and math.isnan(value):
                assert math.isnan(got)
            else:
                assert got == value
