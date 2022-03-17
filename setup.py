from setuptools import setup, find_packages
from os import path

setup(
    name='marspylib',
    packages=find_packages(),
    version="0.1.0",
    description='Library containing python functions to interact with Mars Archives',
    author='Karl Duderstadt, Nadia Huisjes, Thomas Retzer',
    url='https://github.com/duderstadt-lab/marspylib',
    install_requires=[],
    setup_requires=['pytest-runner'],
    tests_requires=['pytest'],
    test_suite='tests'
)
