import os
from . import grf


def open(filename):
    _, ext = os.path.splitext(filename)
    if ext == '.grf':
        return open_grf(filename)
    raise ValueError('Unsupported Filetype')


def open_grf(filename):
    return grf.GRFArchive(filename)
