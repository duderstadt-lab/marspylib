import pytest

def test_flatten():
    '''Test if the test list returns the correct flattened list'''
    assert flatten([('a',1),('a',2),'2',['re','fe']]) == ['a', 1, 'a', 2, '2', 're', 'fe']
