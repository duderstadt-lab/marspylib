import pytest
import marspylib.fret as fret


## To add: all unit tests

## Create a mock archive with some molecules and the required tags to test functions



---
def test_flatten():
    '''Test if the test list returns the correct flattened list'''
    assert marspylib.flatten([('a',1),('a',2),'2',['re','fe']]) == ['a', 1, 'a', 2, '2', 're', 'fe']
