import math

import marspylib.fret as fret
from marspylib.yama.model import Archive, MarsMetadata, MarsPosition, Molecule, Properties


def make_archive(metadata_tags, molecule_positions):
    metadata = MarsMetadata(uid="meta1")
    metadata.tags = list(metadata_tags)
    molecule = Molecule(uid="mol1", metadata_uid="meta1")
    for name, position in molecule_positions.items():
        molecule.positions[name] = MarsPosition(name=name, position=position)
    properties = Properties(archive_type="de.mpg.biochem.mars.molecule.SingleMoleculeArchive")
    return Archive(properties, {"meta1": metadata}, {"mol1": molecule}), molecule


def test_get_T_bleach_fret_uses_later_bleach_position():
    archive, molecule = make_archive(["FRET"], {"Donor_Bleach": 10.0, "Acceptor_Bleach": 25.0})
    assert fret.get_T_bleach(archive, molecule) == 25


def test_get_T_bleach_acceptor_only():
    archive, molecule = make_archive(["AO"], {"Acceptor_Bleach": 15.0})
    assert fret.get_T_bleach(archive, molecule) == 15


def test_get_T_bleach_donor_only():
    archive, molecule = make_archive(["DO"], {"Donor_Bleach": 8.0})
    assert fret.get_T_bleach(archive, molecule) == 8


def test_get_T_bleach_untagged_returns_nan():
    archive, molecule = make_archive([], {})
    assert math.isnan(fret.get_T_bleach(archive, molecule))


def test_get_acceptor_donor_bleach_fret_donor_first():
    archive, molecule = make_archive(["FRET"], {"Donor_Bleach": 5.0, "Acceptor_Bleach": 20.0})
    t_bleach, t_second_bleach, dye = fret.get_acceptor_donor_bleach_fret(archive, molecule)
    assert (t_bleach, t_second_bleach, dye) == (5, 20, ["donor"])


def test_get_acceptor_donor_bleach_fret_acceptor_first():
    archive, molecule = make_archive(["FRET"], {"Donor_Bleach": 30.0, "Acceptor_Bleach": 12.0})
    t_bleach, t_second_bleach, dye = fret.get_acceptor_donor_bleach_fret(archive, molecule)
    assert (t_bleach, t_second_bleach, dye) == (12, 30, ["acceptor"])


def test_get_acceptor_donor_bleach_fret_missing_positions():
    archive, molecule = make_archive(["FRET"], {})
    t_bleach, t_second_bleach, dye = fret.get_acceptor_donor_bleach_fret(archive, molecule)
    assert math.isnan(t_bleach) and math.isnan(t_second_bleach) and dye == ["NaN"]
