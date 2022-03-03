
def figure_to_imgsrc(figure):
    imageBytes = io.BytesIO()
    figure.savefig(imageBytes)
    imageBytes.seek(0)
    imgsrc = imagej.sj.to_java('data:image/png;base64,' + base64.b64encode(imageBytes.read()).decode("utf-8"))
    matplotlib.pyplot.close(figure)
    return imgsrc
