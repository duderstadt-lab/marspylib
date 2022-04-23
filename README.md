**Mars** - **M**olecule **AR**chive **S**uite

Python library with utility functions and converters for working with mars.
Complete Molecule ARchive Suite (Mars) documentation including a guide to
working with mars data structures in python can be found at [mars-docs](https://duderstadt-lab.github.io/mars-docs/).

## Installation

This project should be installed in an activated conda environment containing
pyimagej. This can be accomplished with pip:

```
pip install marspylib
```
This project should soon be available for installation through [conda forge](https://github.com/conda-forge/staged-recipes/pull/18733).

## How to activate Conda Python 3 scripting to Fiji

To add a Conda Python 3 scripting language to Fiji follow the installation
instructions above. Install a local copy of Fiji and activate the Mars update
site. Make sure to fully update Fiji and ensure Mars is functioning properly
and you Fiji includes javafx. The Mars update site will provide the scripting-python
jar required to work with the Conda Python 3 scripting language.

Then launch Fiji from inside your activated conda environment containing pyimagej
and marspylib. You can do this using the launchFiji script included with marspylib:

```
launchFiji /path/to/your/Fiji.app
```

The Fiji gui should appear and you should be able to use the Conda Python 3 scripting
language. Now you will also have full access to Conda Python 3 based features in
Mars.
