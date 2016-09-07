from . import grf


def open_grf(filename: str) -> grf.GRF:
    """open a GRF archive

    :param filename: the path to the grf archive file
    """
    return grf.GRF(open(filename, 'rb'))
