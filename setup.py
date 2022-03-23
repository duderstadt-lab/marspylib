from setuptools import setup, find_packages
from os import path

setup(
    name='marspylib',
    packages=find_packages(),
    version="0.1.0",
    description='Library containing python functions to interact with Mars Archives',
    author='Karl Duderstadt, Nadia Huisjes, Thomas Retzer',
    url='https://github.com/duderstadt-lab/marspylib',
    download_url='https://pypi.org/project/marspylib/',
    project_urls={
        'Documentation': 'https://duderstadt-lab.github.io/mars-docs/'},
    long_description=open(README.md).read(),
    long_description_content_type='text/markdown',

    install_requires=[
        'pandas',
        'numpy',
        'seaborn',
        'matplotlib',
        'imagej',
        'jpype',
        'scyjava',
        'itertools',
        'java.io',
        'scipy',
        'pylab'
    ],
    setup_requires=['pytest-runner'],
    tests_requires=['pytest'],
    test_suite='tests'
)
