import shutil
import tempfile
from pathlib import Path

import pytest

import marspylib.yama as yama
from marspylib.yama.io.store import open_virtual_store

SINGLE_FILE = Path(__file__).parent / "fixtures" / "yama" / "single_molecule_archive.yama"
STORE = Path(__file__).parent / "fixtures" / "yama_store" / "single_molecule_archive.yama.store"


def test_fast_lookups_match_full_records():
    archive = open_virtual_store(STORE)
    assert archive.molecule_tags("mol1") == archive["mol1"].tags
    assert archive.molecule_channel("mol3") == archive["mol3"].channel
    assert archive.molecule_image("mol1") == archive["mol1"].image
    assert archive.molecule_metadata_uid("mol2") == archive["mol2"].metadata_uid
    assert archive.metadata_tags("meta1") == list(archive.metadata)[0].tags


def test_fast_lookups_do_not_trigger_a_full_load():
    archive = open_virtual_store(STORE)
    archive.molecule_tags("mol1")
    archive.molecule_channel("mol1")
    archive.molecule_image("mol1")
    archive.molecule_metadata_uid("mol1")
    archive.molecule_has_tag("mol3", "reviewed")
    archive.metadata_tags("meta1")

    assert len(archive._molecules._cache) == 0
    assert len(archive._metadata._cache) == 0


def test_molecule_has_tag_and_has_tags():
    archive = open_virtual_store(STORE)
    assert archive.molecule_has_tag("mol3", "reviewed") is True
    assert archive.molecule_has_tag("mol2", "reviewed") is False
    assert archive.molecule_has_tags("mol1") is True
    assert archive.molecule_has_tags("mol2") is False


def test_metadata_has_tag_uses_fast_path():
    archive = open_virtual_store(STORE)
    assert archive.metadata_has_tag("meta1", "imported") is True
    assert archive.metadata_has_tag("meta1", "nope") is False
    assert len(archive._metadata._cache) == 0


def test_missing_uid_raises_key_error():
    archive = open_virtual_store(STORE)
    with pytest.raises(KeyError):
        archive.molecule_tags("does_not_exist")


def test_fallback_when_no_index_present():
    with tempfile.TemporaryDirectory() as tmp:
        work = Path(tmp) / "no_index.yama.store"
        shutil.copytree(STORE, work)
        (work / "indexes.sml").unlink()

        archive = open_virtual_store(work)
        assert archive.molecule_tags("mol3") == ["accepted", "reviewed"]
        assert archive.molecule_channel("mol1") == 1


def test_stale_index_entry_invalidated_after_put():
    with tempfile.TemporaryDirectory() as tmp:
        work = Path(tmp) / "work.yama.store"
        shutil.copytree(STORE, work)

        archive = open_virtual_store(work)
        assert archive.molecule_tags("mol1") == ["accepted"]

        mol1 = archive["mol1"]
        mol1.add_tag("freshly_added")
        archive.put(mol1)

        assert archive.molecule_tags("mol1") == ["accepted", "freshly_added"]


def test_removed_uid_no_longer_answered_by_index():
    with tempfile.TemporaryDirectory() as tmp:
        work = Path(tmp) / "work.yama.store"
        shutil.copytree(STORE, work)

        archive = open_virtual_store(work)
        archive.remove("mol1")
        with pytest.raises(KeyError):
            archive.molecule_tags("mol1")


def test_single_file_archive_uses_object_fallback():
    archive = yama.open(SINGLE_FILE)
    assert archive.molecule_tags("mol1") == ["accepted"]
    assert archive.molecule_channel("mol1") == 1
    assert archive.molecule_has_tag("mol3", "reviewed") is True
    assert archive.metadata_tags("meta1") == ["imported"]
