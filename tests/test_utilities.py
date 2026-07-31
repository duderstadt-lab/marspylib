import base64
import pytest
import marspylib
import matplotlib.pyplot as plt

## To add: unit tests gauss()

def test_figure_to_imgsrc():
    '''Test if the generated figure is correctly converted to an img src data string.

    Only checks the data-URI framing and that the payload decodes to a valid
    PNG of the expected pixel dimensions -- not an exact byte match, since
    matplotlib embeds its own version string in the PNG metadata, which
    would otherwise make this test fail on every matplotlib upgrade.
    '''
    plt.plot([1, 2, 3, 4])
    plt.ylabel('some numbers')
    fig = plt.gcf()
    fig.set_size_inches(0.1, 0.1)
    fig.set_dpi(50)
    imgsrc = marspylib.figure_to_imgsrc(fig)

    prefix = 'data:image/png;base64,'
    assert imgsrc.startswith(prefix)

    png_bytes = base64.b64decode(imgsrc[len(prefix):])
    assert png_bytes.startswith(b'\x89PNG\r\n\x1a\n')
    assert png_bytes.endswith(b'IEND\xaeB`\x82')

    # IHDR chunk (right after the 8-byte signature and 4-byte length + "IHDR")
    # holds width/height as two big-endian uint32s. Exact pixel count from a
    # 0.1in x 0.1in @ 50dpi figure varies slightly by matplotlib version
    # (rounding/padding), so just check it rendered as a small square image.
    width = int.from_bytes(png_bytes[16:20], 'big')
    height = int.from_bytes(png_bytes[20:24], 'big')
    assert width == height
    assert 0 < width <= 20

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
