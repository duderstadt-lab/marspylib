from setuptools import setup, find_packages
from os import path

setup(
    name='marspylib',
    packages=find_packages(),
    platforms=['any'],
    version="0.2.0",
    description='Pure-Python library for reading and writing Mars Molecule Archives (.yama) and utility functions for working with them',
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
