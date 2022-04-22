from setuptools import setup, find_packages
from os import path

setup(
    name='marspylib',
    packages=find_packages(),
    platforms=['any'],
    version="0.1.3",
    description='Library containing python Fiji launcher and python functions to interact with Mars Archives',
    author='Karl Duderstadt, Nadia Huisjes, Thomas Retzer',
    url='https://github.com/duderstadt-lab/marspylib',
    install_requires=[
      'jpype1 >=1.3.0',
      'pyimagej',
      'scyjava',
      'matplotlib'
    ],
    scripts=['bin/launchFiji'],
    tests_requires=['pytest']
)
