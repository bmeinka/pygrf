from . import grf
from . import gat


def open_grf(filename: str) -> grf.GRF:
    """open a GRF archive

    :param filename: the path to the grf archive file
    """
    return grf.GRF(open(filename, 'rb'))


def open_gat(filename: str) -> gat.GAT:
    """open a GAT archive

    :param filename: the path to the gat file
    """
    return gat.GAT(open(filename, 'rb'))
