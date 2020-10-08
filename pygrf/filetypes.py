""" This module handles file headers and determining file types """
import struct
from collections import namedtuple
from .exceptions import FileParseError as ParseError


Header = namedtuple('Header', 'signature version size')
_long = struct.Struct('<4sH')
_short = struct.Struct('<2sH')


def parse_header(data: bytes, signature: bytes) -> Header:
    """
    Parse the header of a file.

    data
        The raw bytes data for the file.
    signature
        The file type signature expected to be found at the beginning of the
        file. If the signature is missing or incorrect, an error will be
        raised.
    """
    if not data.startswith(signature):
        raise ParseError('invalid signature')
    if len(signature) == 2:
        return Header(*_short.unpack_from(data), _short.size)
    elif len(signature) == 4:
        return Header(*_long.unpack_from(data), _long.size)
    raise ParseError('invalid signature length')


def parse(stream):
    # TODO: move this to a different module (API?) so that the header parsing
    # can work properly...
    """
    Determine the filetype based on the file type and return the appropriate
    parser.
    """
    stream.seek(0)
    data = stream.read()
    if data.startswith(b'AC'):
        from .act import ACT
        return ACT(stream)
    elif data.startswith(b'SP'):
        from .spr import SPR
        return SPR(data)
    elif data.startswith(b'GRAT'):
        from .gat import GAT
        return GAT(stream)
    return stream
