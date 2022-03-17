## How to set up marspylib as a local package in your conda environment

To be able to use the marspylib functions in your Jupyter notebook or other Python code running environment, follow the procedure below.
Please make sure to install the Conda environment 'pyimagejMars' before according to the mars docs tutorial.


**How to set it up**
1. Clone the repository from github so it is stored locally on your computer.
2. Open a terminal window, activate the 'pyimagejMars' environment.
'''
conda activate pyimagejMars
'''

3. Install the following packages using the conda command.
- wheel
- setuptools
- twine
'''
conda install wheel
'''

4. Build the library using the setup file in the cloned repository. Before doing so, make sure your present working directory is the main folder of the cloned repository. (cd git, cd marspylib). Then build the library as indicated below.
'''
python setup.py bdist_wheel
'''

5. Now find the filepath to the created wheel file. In my case the file path looks like this:
'/Users/nadiahuisjes/git/marspylib/dist/marspylib-0.1.0-py3-none-any.whl'
If you have trouble finding the correct file path, locate the .whl file in the finder window, then drag and drop it into a terminal window. The path to the file will be displayed.

6. Install your package
'''
pip install <path to the .whl file>
'''

**How to use the package**  
To use the package, activate the 'pyimagejMars' environment in the terminal (conda activate pyimagejMars) and launch a jupyter notebook. Open a notebook with the 'pyimagejMars' kernal and import the package similar to how you would also import other packages. For example:

'''
import pandas as pd
import marspylib as ml
import seaborn as sns
'''

Access the functions within the library as usual. For example:
ml.flatten()
ml.fret.get_T_bleach()

Check the file structure in the github repository to find whether a function is part of the main utilities folder, or whether a subdirectory (such as 'fret') needs to be specified.

**How to update**  
In case the github repository is updated, the python package should be updated as well to get access to all new features.

1. Optional: manage your git status by updating your forked repository or by uploading your new function to the main repository.
2. Build a new wheel file: (in the terminal, once you are in the correct directory)
'''
python setup.py bdist_wheel
'''
3. Install the new wheel file as a package in your environment.
3a. In case the wheel file has a new name:
'''
pip install  <path to the .whl file>
'''

3b. In case the wheel file has the same name as the previous wheel file:
'''
pip install --force-reinstall  <path to the .whl file>
'''  
4. Make sure to import the package again in your active notebook.


**How to use the unit tests**  
In the terminal run:
'''
python setup.py pytest
'''



**Source information**  
https://medium.com/analytics-vidhya/how-to-create-a-python-library-7d5aea80cc3f
