import shutil
import tempfile
from pathlib import Path

import marspylib.yama as yama

SINGLE_FILE = Path(__file__).parent / "fixtures" / "yama" / "single_molecule_archive.yama"
STORE = Path(__file__).parent / "fixtures" / "yama_store" / "single_molecule_archive.yama.store"


def test_remove_molecule_single_file():
    archive = yama.open(SINGLE_FILE)
    assert "mol1" in archive
    archive.remove("mol1")
    assert "mol1" not in archive
    assert len(archive) == 2


def test_remove_missing_uid_is_a_no_op():
    archive = yama.open(SINGLE_FILE)
    archive.remove("does_not_exist")   # should not raise
    assert len(archive) == 3


def test_remove_metadata_single_file():
    archive = yama.open(SINGLE_FILE)
    meta_uid = next(iter(archive.metadata)).uid
    assert archive.contains_metadata(meta_uid)
    archive.remove_metadata(meta_uid)
    assert not archive.contains_metadata(meta_uid)


def test_remove_persists_after_save():
    archive = yama.open(SINGLE_FILE)
    archive.remove("mol1")
    with tempfile.TemporaryDirectory() as tmp:
        out_path = Path(tmp) / "out.yama"
        archive.save(out_path)
        reopened = yama.open(out_path)
    assert "mol1" not in reopened
    assert len(reopened) == 2
    assert reopened.properties.number_of_molecules == 2


def test_remove_deletes_file_immediately_in_virtual_store():
    with tempfile.TemporaryDirectory() as tmp:
        work_store = Path(tmp) / "work.yama.store"
        shutil.copytree(STORE, work_store)

        archive = yama.open(work_store)
        assert (work_store / "Molecules" / "mol1.sml").exists()

        archive.remove("mol1")

        # deleted immediately, not deferred to save()
        assert not (work_store / "Molecules" / "mol1.sml").exists()
        assert "mol1" not in archive
        assert len(archive) == 2


def test_remove_metadata_deletes_file_immediately_in_virtual_store():
    with tempfile.TemporaryDirectory() as tmp:
        work_store = Path(tmp) / "work.yama.store"
        shutil.copytree(STORE, work_store)

        archive = yama.open(work_store)
        assert (work_store / "Metadata" / "meta1.sml").exists()

        archive.remove_metadata("meta1")

        assert not (work_store / "Metadata" / "meta1.sml").exists()
        assert not archive.contains_metadata("meta1")


def test_virtual_store_remove_then_save_reflects_in_index():
    with tempfile.TemporaryDirectory() as tmp:
        work_store = Path(tmp) / "work.yama.store"
        shutil.copytree(STORE, work_store)

        archive = yama.open(work_store)
        archive.remove("mol1")
        archive.save()

        reopened = yama.open(work_store)
        assert len(reopened) == 2
        assert "mol1" not in reopened.molecule_uids()
        assert reopened.properties.number_of_molecules == 2


def test_is_virtual():
    assert yama.open(SINGLE_FILE).is_virtual is False
    assert yama.open(STORE).is_virtual is True


def test_molecule_and_metadata_uids_without_loading():
    archive = yama.open(SINGLE_FILE)
    assert set(archive.molecule_uids()) == {"mol1", "mol2", "mol3"}
    assert set(archive.metadata_uids()) == {"meta1"}


def test_uids_cheap_for_virtual_store():
    archive = yama.open(STORE)
    assert set(archive.molecule_uids()) == {"mol1", "mol2", "mol3"}
    assert set(archive.metadata_uids()) == {"meta1"}


def test_get_set_comments():
    archive = yama.open(SINGLE_FILE)
    assert archive.get_comments() == ""
    archive.set_comments("some notes about this archive")
    assert archive.get_comments() == "some notes about this archive"
    assert archive.properties.documents["Comments"].content == "some notes about this archive"
