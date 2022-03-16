import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns



def figure_to_imgsrc(figure):
    '''[]
    @Author: Karl E. Duderstadt'''
    imageBytes = io.BytesIO()
    figure.savefig(imageBytes)
    imageBytes.seek(0)
    imgsrc = imagej.sj.to_java('data:image/png;base64,' + base64.b64encode(imageBytes.read()).decode("utf-8"))
    matplotlib.pyplot.close(figure)
    return imgsrc

def flatten(list_to_convert):
    '''Take a list of lists and return the flattened list
    @Author: Nadia M. Huisjes'''
    return [item for sublist in list_to_convert for item in sublist]
