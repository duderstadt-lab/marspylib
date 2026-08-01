import numpy as np

## marspylib.fret

def get_T_bleach(archive, molecule, metadata_tag_populations = ['FRET', 'AO', 'DO'], names_bleaching_events = ['Donor_Bleach', 'Acceptor_Bleach']):
    """Returns the T_bleach position for a molecule.

    Args:
        archive: The marspylib.yama.Archive the molecule belongs to.
        molecule: The marspylib.yama.Molecule record to inspect.
        metadata_tag_populations: Tags present in the archive denoting molecules displaying FRET
            behavior, that have an acceptor only (AO), or donor only (DO), in that order.
            Defaults to ['FRET', 'AO', 'DO'].
        names_bleaching_events: Position names of the donor and acceptor bleaching events in the
            archive, in that order. Defaults to ['Donor_Bleach', 'Acceptor_Bleach'].

    Returns:
        T_bleach: the T-position of the bleaching point where either one of the dyes (donor or
        acceptor) has bleached. Numerical value.

    Author: Nadia M. Huisjes
    """
    if (archive.metadata_has_tag(molecule.metadata_uid, metadata_tag_populations[0])):
                if (molecule.has_position(names_bleaching_events[1]) & molecule.has_position(names_bleaching_events[0])):
                    T_AO_bleach = molecule.get_position(names_bleaching_events[1]).position
                    T_DO_bleach = molecule.get_position(names_bleaching_events[0]).position

                    if int(T_AO_bleach) > int(T_DO_bleach):
                        T_bleach = int(T_AO_bleach)
                    else:
                        T_bleach = int(T_DO_bleach)

    # Molecules in an AO dataset
    elif (archive.metadata_has_tag(molecule.metadata_uid, metadata_tag_populations[1])):
        T_bleach = int(molecule.get_position(names_bleaching_events[1]).position)

    # Molecules in a DO dataset
    elif (archive.metadata_has_tag(molecule.metadata_uid, metadata_tag_populations[2])):
        T_bleach = int(molecule.get_position(names_bleaching_events[0]).position)

    else:
        T_bleach = np.nan

    return T_bleach



def get_acceptor_donor_bleach_fret(archive, molecule, metadata_tag_fret = 'FRET', names_bleaching_events = ['Donor_Bleach', 'Acceptor_Bleach']):
    """Returns the T_bleach position for a molecule.

    IMPORTANT: both bleaching positions are only retrieved if the molecule has a metadata tag
    representing a FRET molecule.

    Args:
        archive: The marspylib.yama.Archive the molecule belongs to.
        molecule: The marspylib.yama.Molecule record to inspect.
        metadata_tag_fret: Tag present in the archive denoting molecules displaying FRET behavior.
            Defaults to 'FRET'.
        names_bleaching_events: Position names of the donor and acceptor bleaching events in the
            archive, in that order. Defaults to ['Donor_Bleach', 'Acceptor_Bleach'].

    Returns:
        A tuple of three values:

        - T_bleach: the T-position of the bleaching point where the first dye has bleached. Numerical value.
        - T_second_bleach: the T-position of the bleaching point where the second dye has bleached. Numerical value.
        - dye: list with one string representing which dye is associated with the defined T_bleach.

    Author: Nadia M. Huisjes
    """

    if (archive.metadata_has_tag(molecule.metadata_uid, metadata_tag_fret)):
                if (molecule.has_position(names_bleaching_events[1]) & molecule.has_position(names_bleaching_events[0])):
                    T_AO_bleach = molecule.get_position(names_bleaching_events[1]).position
                    T_DO_bleach = molecule.get_position(names_bleaching_events[0]).position

                    if int(T_AO_bleach) < int(T_DO_bleach):
                        T_bleach = int(T_AO_bleach)
                        T_second_bleach = int(T_DO_bleach)
                        dye = ['acceptor']
                    else:
                        T_bleach = int(T_DO_bleach)
                        T_second_bleach = int(T_AO_bleach)
                        dye = ['donor']

                else:
                    T_bleach = np.nan
                    T_second_bleach = np.nan
                    dye = ['NaN']

    return (T_bleach, T_second_bleach, dye)
