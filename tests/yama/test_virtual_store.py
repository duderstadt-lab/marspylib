import math
import shutil
import tempfile
from pathlib import Path

import marspylib.yama as yama
from marspylib.yama.io.store import _LazyMetadataMap, _LazyMoleculeMap

STORE = Path(__file__).parent / "fixtures" / "yama_store" / "single_molecule_archive.yama.store"


def test_open_dispatches_to_virtual_store():
    archive = yama.open(STORE)
    assert isinstance(archive._molecules, _LazyMoleculeMap)
    assert isinstance(archive._metadata, _LazyMetadataMap)


def test_properties_and_membership():
    archive = yama.open(STORE)
    assert archive.properties.archive_type == "de.mpg.biochem.mars.molecule.SingleMoleculeArchive"
    assert archive.properties.number_of_molecules == 3
    assert len(archive) == 3
    assert "mol1" in archive and "mol2" in archive and "mol3" in archive
    assert "nope" not in archive


def test_lazy_molecule_loading():
    archive = yama.open(STORE)
    mol1 = archive["mol1"]
    assert mol1.tags == ["accepted"]
    assert mol1.parameters["dwell"] == 5.5
    assert list(mol1.table.columns) == ["T", "Intensity", "label"]
    assert math.isnan(mol1.table["Intensity"][3])

    mol3 = archive["mol3"]
    assert mol3.tags == ["accepted", "reviewed"]
    assert mol3.channel == 2
    assert mol3.parameters["dwell"] == 9.25


def test_molecule_cache_returns_same_object():
    archive = yama.open(STORE)
    first = archive["mol1"]
    second = archive["mol1"]
    assert first is second


def test_full_iteration():
    archive = yama.open(STORE)
    uids = sorted(m.uid for m in archive)
    assert uids == ["mol1", "mol2", "mol3"]


def test_lazy_metadata_loading_and_tag_check():
    archive = yama.open(STORE)
    metas = list(archive.metadata)
    assert len(metas) == 1
    assert metas[0].uid == "meta1"
    assert archive.metadata_has_tag("meta1", "imported")
    assert not archive.metadata_has_tag("meta1", "nope")


def test_save_in_place_updates_store():
    with tempfile.TemporaryDirectory() as tmp:
        work_store = Path(tmp) / "work.yama.store"
        shutil.copytree(STORE, work_store)

        archive = yama.open(work_store)
        archive["mol1"].add_tag("python_edited")
        archive["mol2"].parameters["new_param"] = 3.75
        archive.save()

        reopened = yama.open(work_store)
        assert reopened["mol1"].tags == ["accepted", "python_edited"]
        assert reopened["mol2"].parameters["new_param"] == 3.75
        # untouched records survive the round-trip unchanged
        assert reopened["mol3"].tags == ["accepted", "reviewed"]
        assert list(reopened.metadata)[0].uid == "meta1"


def test_save_in_place_index_reflects_current_state():
    from marspylib.yama.smile.reader import SmileReader, read_generic_value

    with tempfile.TemporaryDirectory() as tmp:
        work_store = Path(tmp) / "work.yama.store"
        shutil.copytree(STORE, work_store)

        archive = yama.open(work_store)
        archive["mol1"].add_tag("python_edited")
        archive.save()

        reader = SmileReader((work_store / "indexes.sml").read_bytes())
        index = read_generic_value(reader, reader.next_token())
        by_uid = {m["uid"]: m for m in index["molecules"]}
        assert by_uid["mol1"]["tags"] == ["accepted", "python_edited"]
        assert by_uid["mol1"]["metadataUID"] == "meta1"
        assert by_uid["mol1"]["channel"] == 1
        assert {m["uid"] for m in index["metadata"]} == {"meta1"}


def test_save_single_file_archive_as_new_virtual_store():
    single_file = Path(__file__).parent / "fixtures" / "yama" / "single_molecule_archive.yama"
    archive = yama.open(single_file)
    with tempfile.TemporaryDirectory() as tmp:
        new_store = Path(tmp) / "new.yama.store"
        archive.save(new_store)
        reopened = yama.open(new_store)

        # lazy-loaded records need the directory to still exist -- assert
        # while still inside the tempdir's lifetime, not after
        assert len(reopened) == 3
        assert reopened["mol3"].tags == ["accepted", "reviewed"]
        assert reopened["mol1"].table["label"].tolist()[0] == "f0"


def test_flatten_to_single_file():
    archive = yama.open(STORE)
    with tempfile.TemporaryDirectory() as tmp:
        out_path = Path(tmp) / "flattened.yama"
        archive.save(out_path)
        flat = yama.open(out_path)

    assert len(flat) == 3
    assert flat["mol3"].tags == ["accepted", "reviewed"]
    assert flat["mol1"].parameters["dwell"] == 5.5


def test_missing_indexes_falls_back_to_directory_scan():
    with tempfile.TemporaryDirectory() as tmp:
        copy_path = Path(tmp) / "no_index.yama.store"
        shutil.copytree(STORE, copy_path)
        (copy_path / "indexes.sml").unlink()

        archive = yama.open(copy_path)
        assert len(archive) == 3
        assert sorted(m.uid for m in archive) == ["mol1", "mol2", "mol3"]
        assert archive["mol3"].tags == ["accepted", "reviewed"]
