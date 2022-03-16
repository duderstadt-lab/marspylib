import pytest
import marspylib


## To add: unit tests figure_to_imgsrc(), gauss()

def test_flatten():
    '''Test if the test list returns the correct flattened list'''
    assert marspylib.flatten([('a',1),('a',2),'2',['re','fe']]) == ['a', 1, 'a', 2, '2', 're', 'fe']

def test_gauss():
    '''Test if a set of known parameters returns the correct
    predicted y-coordinates'''
    x_vals = [1,2,3,200,5000]
    y_vals = []
    for x in x_vals:
        y_vals.append(gauss(x,-20,5,0.5))
    assert y_vals == [7.387418011601682e-05,3.126075188741013e-05,1.2709673258099624e-05,0.0,0.0]
