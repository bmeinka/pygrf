from . import act, gat, spr


SIGNATURES = {
    b'AC': act.ACT,
    b'SP': spr.SPR,
    b'GRAT\x01\x02': gat.GAT,
}


def parse(stream):
    """ determine the parser to use for a file based on its header signature """
    for signature, parser in SIGNATURES.items():
        stream.seek(0)
        if signature == stream.read(len(signature)):
            return parser(stream)
    return stream