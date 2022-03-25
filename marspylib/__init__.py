import matplotlib.pyplot as plt
import io
import base64
import math

def hallo_world():
    print('hallo world')

## Utility functions

def figure_to_imgsrc(figure):
    '''Used with mars widgets to convert a matplotlib figure into a
    data string. Renders the figure provided and converts the
    resulting image to a base64-encoded string with an html data
    format prefix.

    @Author: Karl E. Duderstadt'''
    imageBytes = io.BytesIO()
    figure.savefig(imageBytes)
    imageBytes.seek(0)
    imgsrc = 'data:image/png;base64,' + base64.b64encode(imageBytes.read()).decode("utf-8")
    plt.close(figure)
    return imgsrc

def flatten(list_to_convert):
    '''Take a list of lists and return the flattened list.

    Inputs
    list_to_convert: a list of items that needs to be flattened

    Outputs
    list: flattened list containing all items present in list_to_convert

    @Author: Nadia M. Huisjes'''
    return [item for sublist in list_to_convert for item in sublist]


def gauss(x,mu,sigma,A):
    '''Defines the formula for a Gaussian curve. Can either be used
    for fitting to data that is expected to be distributed as such,
    or for plotting the fitted curve to the original data.

    Inputs
    x: x-coordinates for which a Gaussian curve is calculated.
    mu: mean of the distribution
    sigma: standard deviation of the distribution
    A: scaling constant

    Outputs
    y: corresponding y-coordinates for the calculated x-coordinates.

    @Author: Nadia M. Huisjes'''
    return A*math.exp(-(x-mu)**2/2/sigma**2)
