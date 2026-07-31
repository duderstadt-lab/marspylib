from setuptools import setup, find_packages
from os import path

this_directory = path.abspath(path.dirname(__file__))
with open(path.join(this_directory, 'README.md'), encoding='utf-8') as f:
    long_description = f.read()

setup(
    name='marspylib',
    packages=find_packages(),
    platforms=['any'],
    version="0.3.0",
    description='Pure-Python library for reading and writing Mars Molecule Archives (.yama) and utility functions for working with them',
    long_description=long_description,
    long_description_content_type='text/markdown',
    author='Karl Duderstadt, Nadia Huisjes, Thomas Retzer',
    url='https://github.com/duderstadt-lab/marspylib',
    install_requires=[
      'numpy',
      'pandas',
      'matplotlib'
    ],
    extras_require={
      's3': ['boto3'],
    },
    tests_requires=['pytest']
)
