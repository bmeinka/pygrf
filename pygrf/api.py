from . import grf, gat, spr, act


def open_grf(filename: str) -> grf.GRF:
    """
    Open a GRF archive

    :param filename: the path to the grf archive file
    """
    return grf.GRF(open(filename, 'rb'))


def open_gat(filename: str) -> gat.GAT:
    """
    Open a GAT file

    :param filename: the path to the gat file
    """
    return gat.GAT(open(filename, 'rb'))


def open_spr(filename: str) -> spr.SPR:
    """
    Open a SPR file

    :param filename: the path to the spr file
    """
    with open(filename, 'rb') as f:
        return spr.SPR(f.read())


def open_act(filename: str) -> act.ACT:
    """
    Open a ACT file

    :param filename: the path to the act file
    """
    return act.ACT(open(filename, 'rb'))
