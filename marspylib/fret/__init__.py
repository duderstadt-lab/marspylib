import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns

def hallo_world():
    print('hallo world fret')

## marspylib.fret

def get_T_bleach(molecule, metadata_tag_populations = ['FRET', 'AO', 'DO'], names_bleaching_events = ['Donor_Bleach', 'Acceptor_Bleach']):
    '''
    Function that returns the T_bleach position for a molecule.

    Requirements
    archive: an archive should have been initiated prior to running this function.

    Inputs
    molecule: the variable 'molecule', representing a single molecule record in the archive, should
        have been defined prior to running this function.
    metadata_tag_populations: default ['FRET', 'AO', 'DO'], list with strings denoting the tags present in the
        archive to tag molecules displaying FRET behavior, that have an acceptor only (AO) or donor only (DO).
        Note: names have to be entered in the specific order (FRET name, AO name, DO name).
    names_bleaching_events: default ['Donor_Bleach', 'Acceptor_Bleach'], list with strings denoting the position
        names of the donor and bleaching events in the archive.
        Note: names have to be entered in the specific order (Donor bleaching name, Acceptor bleaching name).

    Outputs
    T_bleach: the T-position of the bleaching point where either one of the dyes (donor or acceptor) has bleached.
        Numerical value.

    @Author: Nadia M. Huisjes
    '''
    if (archive.metadataHasTag(molecule.getMetadataUID(),metadata_tag_populations[0])):
                if (molecule.hasPosition(names_bleaching_events[1]) & molecule.hasPosition(names_bleaching_events[0])):
                    T_AO_bleach = molecule.getPosition(names_bleaching_events[1]).getPosition()
                    T_DO_bleach = molecule.getPosition(names_bleaching_events[0]).getPosition()

                    if int(T_AO_bleach) > int(T_DO_bleach):
                        T_bleach = int(T_AO_bleach)
                    else:
                        T_bleach = int(T_DO_bleach)

    # Molecules in an AO dataset
    elif (archive.metadataHasTag(molecule.getMetadataUID(),metadata_tag_populations[1])):
        T_bleach = int(molecule.getPosition(names_bleaching_events[1]).getPosition())

    # Molecules in a DO dataset
    elif (archive.metadataHasTag(molecule.getMetadataUID(),metadata_tag_populations[2])):
        T_bleach = int(molecule.getPosition(names_bleaching_events[0]).getPosition())

    else:
        T_bleach = np.NaN

    return T_bleach



def get_acceptor_donor_bleach_fret(molecule, metadata_tag_fret = 'FRET', names_bleaching_events = ['Donor_Bleach', 'Acceptor_Bleach']):
    '''
    Function that returns the T_bleach position for a molecule. IMPORTANT: both bleaching positions are only retrieved
        in the case the molecule has a metadata tag representing a FRET molecule.

    Requirements
    archive: an archive should have been initiated prior to running this function.

    Inputs
    molecule: the variable molecule, representing a single molecule record in the archive, should
        have been defined prior to running this function. By default set to the name molecule.
    metadata_tag_fret: default 'FRET', string denoting the tags present in the archive to tag molecules displaying
        FRET behavior.
    names_bleaching_events: default ['Donor_Bleach', 'Acceptor_Bleach'], list with strings denoting the position
        names of the donor and bleaching events in the archive.
        Note: names have to be entered in the specific order (Donor bleaching name, Acceptor bleaching name).

    Outputs (tuple with the following three parameters)
    T_bleach: the T-position of the bleaching point where there first dye has bleached. Numerical value.
    T_second_bleach:the T-position of the bleaching point where there second dye has bleached. Numerical value.
    dye: list with one string representing which dye is associated with the defined T_bleach

    @Author: Nadia M. Huisjes
    '''

    if (archive.metadataHasTag(molecule.getMetadataUID(),metadata_tag_fret)):
                if (molecule.hasPosition(names_bleaching_events[1]) & molecule.hasPosition(names_bleaching_events[0])):
                    T_AO_bleach = molecule.getPosition(names_bleaching_events[1]).getPosition()
                    T_DO_bleach = molecule.getPosition(names_bleaching_events[0]).getPosition()

                    if int(T_AO_bleach) < int(T_DO_bleach):
                        T_bleach = int(T_AO_bleach)
                        T_second_bleach = int(T_DO_bleach)
                        dye = ['acceptor']
                    else:
                        T_bleach = int(T_DO_bleach)
                        T_second_bleach = int(T_AO_bleach)
                        dye = ['donor']

                else:
                    T_bleach = np.NaN
                    T_second_bleach = np.NaN
                    dye = ['NaN']

    return (T_bleach, T_second_bleach, dye)
