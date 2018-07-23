import struct
from .exceptions import FileParseError


def get_version(stream, signature, supported=None):
    """
    Get the version number of a file and verify its signature

    :param stream: the stream to read the version information from
    :param signature: the signature that must be found at the beginning of the file
    :param supported: the list of supported versions
    """
    # get the position so that we can return to it after we are done
    pos = stream.tell()

    # read the signature and ensure that it is correct
    stream.seek(0)
    if signature != stream.read(len(signature)):
        raise FileParseError('invalid signature')

    # verify the version number
    version, = struct.unpack('<H', stream.read(2))
    if supported and not version in supported:
        raise FileParseError('unsupported version')

    return version
