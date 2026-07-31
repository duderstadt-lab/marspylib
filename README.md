**Mars** - **M**olecule **AR**chive **S**uite

Pure-Python library for reading and writing Mars Molecule Archives (`.yama`)
and utility functions for working with them — no JVM, no Fiji install
required. Complete Molecule ARchive Suite (Mars) documentation including a
guide to working with mars data structures in python can be found at
[mars-docs](https://duderstadt-lab.github.io/mars-docs/).

## Installation

```
pip install marspylib
```

This project should soon be available for installation through [conda forge](https://github.com/conda-forge/staged-recipes/pull/18733).

Only dependency requirements are `numpy`, `pandas`, and `matplotlib` — this
package can be installed in any plain Python/conda environment and does not
require Fiji, ImageJ, or a JVM of any kind.

## Usage

```python
import marspylib.yama as yama

archive = yama.open("experiment.yama")
print(archive.properties.number_of_molecules)

for molecule in archive:
    df = molecule.table            # pandas.DataFrame
    if "accepted" in molecule.tags:
        ...

molecule = archive["some-uid"]     # random access by UID

archive.save("experiment_out.yama")
```
