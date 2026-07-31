import shutil
import tempfile
from pathlib import Path

import marspylib.yama as yama
from marspylib.yama.io.store import open_virtual_store
from marspylib.yama.model import MarsMetadata, SingleMolecule

SINGLE_FILE = Path(__file__).parent / "fixtures" / "yama" / "single_molecule_archive.yama"
STORE = Path(__file__).parent / "fixtures" / "yama_store" / "single_molecule_archive.yama.store"


def test_put_adds_new_molecule_to_single_file_archive():
    archive = yama.open(SINGLE_FILE)
    assert "mol_new" not in archive

    mol = SingleMolecule(uid="mol_new")
    mol.add_tag("brand_new")
    archive.put(mol)

    assert "mol_new" in archive
    assert archive["mol_new"].tags == ["brand_new"]
    assert len(archive) == 4


def test_put_replaces_existing_molecule():
    archive = yama.open(SINGLE_FILE)
    replacement = SingleMolecule(uid="mol1")
    replacement.add_tag("replaced")
    archive.put(replacement)

    assert archive["mol1"] is replacement
    assert archive["mol1"].tags == ["replaced"]


def test_put_metadata_adds_new_record():
    archive = yama.open(SINGLE_FILE)
    meta = MarsMetadata(uid="meta_new", microscope="NewScope")
    archive.put_metadata(meta)

    assert archive.get_metadata("meta_new") is meta
    assert len(list(archive.metadata)) == 2


def test_save_recomputes_properties_aggregates():
    archive = yama.open(SINGLE_FILE)
    mol = SingleMolecule(uid="mol_new")
    mol.add_tag("fresh_tag")
    mol.parameters["fresh_param"] = 1.0
    mol.channel = 5
    archive.put(mol)

    with tempfile.TemporaryDirectory() as tmp:
        out_path = Path(tmp) / "out.yama"
        archive.save(out_path)
        reopened = yama.open(out_path)

    assert reopened.properties.number_of_molecules == 4
    assert "fresh_tag" in reopened.properties.tag_set
    assert "fresh_param" in reopened.properties.parameter_set
    assert 5 in reopened.properties.channel_set


def test_put_pins_a_mutated_molecule_past_lru_eviction():
    """The scenario that motivated put(): a virtual-store molecule you've
    mutated must survive to save() even if it falls out of the (bounded)
    LRU read-cache before you save -- put() is what guarantees that."""
    with tempfile.TemporaryDirectory() as tmp:
        work_store = Path(tmp) / "work.yama.store"
        shutil.copytree(STORE, work_store)

        archive = open_virtual_store(work_store, molecule_cache_size=1)
        mol1 = archive["mol1"]
        mol1.add_tag("pinned_edit")
        archive.put(mol1)

        # touch other molecules to evict mol1 from a cache that only holds 1 entry
        _ = archive["mol2"]
        _ = archive["mol3"]

        archive.save()

        reopened = open_virtual_store(work_store, molecule_cache_size=1)
        assert reopened["mol1"].tags == ["accepted", "pinned_edit"]


def test_mutation_without_put_can_be_lost_after_eviction():
    """Documents the known limitation put() exists to solve: editing a
    virtual-store molecule without put()-ing it is only safe if it's still
    cached (or you keep your own reference) when save() runs."""
    with tempfile.TemporaryDirectory() as tmp:
        work_store = Path(tmp) / "work.yama.store"
        shutil.copytree(STORE, work_store)

        archive = open_virtual_store(work_store, molecule_cache_size=1)
        archive["mol1"].add_tag("unpinned_edit")   # no reference kept, no put()
        _ = archive["mol2"]
        _ = archive["mol3"]                         # evicts mol1 from the size-1 cache
        archive.save()

        reopened = open_virtual_store(work_store, molecule_cache_size=1)
        assert reopened["mol1"].tags == ["accepted"]   # edit was lost, as expected


def test_put_new_molecule_in_virtual_store_appears_on_disk():
    with tempfile.TemporaryDirectory() as tmp:
        work_store = Path(tmp) / "work.yama.store"
        shutil.copytree(STORE, work_store)

        archive = open_virtual_store(work_store)
        mol = SingleMolecule(uid="mol_new")
        mol.add_tag("added_to_store")
        archive.put(mol)
        archive.save()

        assert (work_store / "Molecules" / "mol_new.sml").exists()
        reopened = open_virtual_store(work_store)
        assert len(reopened) == 4
        assert reopened["mol_new"].tags == ["added_to_store"]
        assert reopened.properties.number_of_molecules == 4
