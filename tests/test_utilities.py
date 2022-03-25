import pytest
import marspylib
import matplotlib.pyplot as plt

## To add: unit tests figure_to_imgsrc(), gauss()

def test_figure_to_imgsrc():
    '''Test if the generated figure is correctly converted to an img src data string'''
    plt.plot([1, 2, 3, 4])
    plt.ylabel('some numbers')
    fig = plt.gcf()
    fig.set_size_inches(0.1, 0.1)
    fig.set_dpi(50)
    assert figure_to_imgsrc(fig) == 'data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAcAAAAHCAYAAADEUlfTAAAAOXRFWHRTb2Z0d2FyZQBNYXRwbG90bGliIHZlcnNpb24zLjUuMSwgaHR0cHM6Ly9tYXRwbG90bGliLm9yZy/YYfK9AAAACXBIWXMAAAsTAAALEwEAmpwYAAAAlklEQVR4nHWOIQrCYABG32+w/EkwCAtDMCwq/00sHsLugmcYiHcwGSxL6hF+g7YNDzDQ5IqK8zPoxOKrDx7PSOIfBvDWWhdFEQCn8kZxuXIvjmck4ZyTJM23ucI41XixE+AbdSJZZySbnOEgYDbqf9O+FXQVxqkmy70e1VN6j3gk0ez0NF0dVH1ELY0kjDElkP2MtgH7Ap5xTn0Bv6XKAAAAAElFTkSuQmCC'

def test_flatten():
    '''Test if the test list returns the correct flattened list'''
    assert marspylib.flatten([('a',1),('a',2),'2',['re','fe']]) == ['a', 1, 'a', 2, '2', 're', 'fe']

def test_gauss():
    '''Test if a set of known parameters returns the correct
    predicted y-coordinates'''
    x_vals = [1,2,3,200,5000]
    y_vals = []
    for x in x_vals:
        y_vals.append(marspylib.gauss(x,-20,5,0.5))
    assert y_vals == [7.387418011601682e-05,3.126075188741013e-05,1.2709673258099624e-05,0.0,0.0]
