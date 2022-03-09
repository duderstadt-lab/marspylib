def flatten(t):
    '''Take a list of lists and return the flattened list'''
    return [item for sublist in t for item in sublist]
