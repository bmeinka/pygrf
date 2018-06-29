from . import grf, gat, spr


def open_grf(filename: str) -> grf.GRF:
    """open a GRF archive

    :param filename: the path to the grf archive file
    """
    return grf.GRF(open(filename, 'rb'))


def open_gat(filename: str) -> gat.GAT:
    """open a GAT file

    :param filename: the path to the gat file
    """
    return gat.GAT(open(filename, 'rb'))


def open_spr(filename: str) -> spr.SPR:
    """open a SPR file

    :param filename: the path to the spr file
    """
    return spr.SPR(open(filename, 'rb'))
