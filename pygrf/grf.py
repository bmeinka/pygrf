import os
from struct import unpack
from zlib import decompress
from collections import namedtuple


# the grf versions that are supported
SUPPORTED_VERSIONS = [0x200]

# where the grf header is located
HEADER_OFFSET = 0
HEADER_LENGTH = 46

# which encodings to try before giving up on a filename
ENCODINGS = ['euc_kr', 'johab', 'uhc', 'mskanji']

FILE_HEADER_LENGTH = 17

# file flags
FILE_IS_FILE = 1


Header = namedtuple('GRFHeader', (
    'allow_encryption', 'index_offset', 'file_count', 'version'
))


FileHeader = namedtuple('GRFFileHeader', (
    'compressed_size', 'archived_size', 'real_size', 'flag', 'position'
))


def decode_name(name):
    """decode a name using multiple encodings"""
    for encoding in ENCODINGS:
        try:
            return name.decode(encoding)
        except UnicodeDecodeError as err:
            pass
    raise UnicodeError(name)


def parse_header(stream):
    """parse the grf header

    :param stream: a byte stream of the grf file

    The header portion of the GRF archive is the first 46 bytes. They are
    arranged as follows:

    ======  ====  =======================================
    offset  size  purpose
    ======  ====  =======================================
    0       15    a watermark that says 'Master of Magic'
    15      15    an encryption flag
    30      4     the offset where the file list is found
    34      8     the number of files in the archive
    42      4     the archive version number
    ======  ====  =======================================

    All integers are stored in little endian byte order.

    Master of Magic
    ===============

    The first 15 bytes of the GRF archive must contain 'Master of Magic'. Any
    other value is invalid.

    Encryption Flag
    ===============

    The encryption flag can be one of two values:

    - 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00
    - 00 01 02 03 04 05 06 07 08 09 0A 0B 0C 0D 0E

    The first flag denotes a file that does not allow encrypted files within.
    The second flag denotes a file that does. Any other value found here is
    invalid.

    Offset
    ======

    The offset is where the file list is found. The stored value does not
    incldue the 46 byte header, but the parsed value does.

    File Count
    ==========

    The file count is stored in two different integers. The first one is
    subtracted from the second, and 7 is taken away to get the total number of
    files stored in the archive.

    .. TODO:: figure out what these two different values actually mean

    Version
    =======

    The version is stored in two bytes. The first byte represents the major
    version number and the second byte is the minor version number. The minor
    version number is ignored by this parser. Currently, the only supported
    version is `0x0200`.
    """
    ENCRYPTION_FLAGS = {bytes(range(15)): True, bytes([0] * 15): False}

    WATERMARK = slice(0, 15)
    ENCRYPTION = slice(15, 30)
    OFFSET = slice(30, 34)
    FILECOUNT = slice(34, 42)
    VERSION = slice(42, 46)

    # read the full header data
    stream.seek(HEADER_OFFSET)
    data = stream.read(HEADER_LENGTH)

    # verify the watermark is valid
    if not data[WATERMARK] == b'Master of Magic':
        raise ValueError('Invalid GRF Header: missing Master of Magic')

    # verify the encryption flag is valid
    try:
        encryption = ENCRYPTION_FLAGS[data[ENCRYPTION]]
    except KeyError:
        raise ValueError('Invalid GRF Header: invalid encryption flag')

    # get the position of the file list
    offset, = unpack('<I', data[OFFSET])
    offset += HEADER_LENGTH

    # get the number of files
    b, a = unpack('<II', data[FILECOUNT])
    file_count = a - b - 7
    if file_count < 0:
        raise ValueError('Invalid GRF Header: invalid file count')

    # get the version
    version, = unpack('<I', data[VERSION])
    version &= 0xff00  # ignore minor version information
    if version not in SUPPORTED_VERSIONS:
        raise ValueError('Invalid GRF Header: unsupported version')

    return Header(encryption, offset, file_count, version)


def parse_index(stream, header):
    """parse the list of files

    :param stream: the byte stream of the grf file
    :param header: the grf header information
    :returns: a grf index
    """
    # seek to and read the size information
    stream.seek(header.index_offset)
    compressed_length, real_length = unpack('<II', stream.read(8))

    # read and decompress the index data
    index_data = decompress(stream.read(compressed_length))

    index = {}
    for _ in range(header.file_count):
        # pop the filename off the top
        filename, index_data = index_data.split(b'\x00', 1)
        filename = decode_name(filename)

        # pop the header off the top
        header = index_data[:FILE_HEADER_LENGTH]
        index_data = index_data[FILE_HEADER_LENGTH:]

        # append the file to the index
        index[filename] = header

    return index


def parse_file_header(data):
    """parse file header

    :param header_data: the raw header data to parse

    The file header is made up of 17 bytes of information arranged in the
    following way:

    ======  ====  ===============
    offset  size  purpose
    ======  ====  ===============
    0       12    sizes
    12      1     flags
    13      4     position
    ======  ====  ===============

    All integers are stored in little endian byte order.

    Sizes
    =====

    There are three different sizes stored in this order:

    compressed size
        the size of the compressed file data
    size in file
        the size of the data stored in the archive itself
    real size
        the full, decompressed file size

    Flags
    =====

    The flag byte stores information about the file and how it is stored within
    the archive. The flags are:

    =====  =================================================
    value  purpose
    =====  =================================================
    0x1    if set, this is a file. if not, it is a directory
    0x2    set if the file uses mixed encryption
    0x4    set if only the first 0x14 bytes are encrypted
    =====  =================================================

    .. TODO:: find files with flags other than 0x01

    Position
    ========

    This is the offset at which the file is stored in the archive. The stored
    value does not include the 46 byte header. The parsed value does.
    """
    SIZES = slice(0, 12)
    FLAG = 12
    POSITION = slice(13, 17)

    compressed, archived, real = unpack('<III', data[SIZES])
    flag = data[FLAG]
    position, = unpack('<I', data[POSITION])
    position += HEADER_LENGTH

    return FileHeader(compressed, archived, real, flag, position)


class GRFFile:

    def __init__(self, filename, stream, header_data):
        """fetch file from grf archive

        :param stream: the grf file stream
        :param header_data: the header data for this file
        """
        self.filename = filename
        self.header = parse_file_header(header_data)
        # raise value error if flags trigger unsupported action

        # seek to, read, and decompress file data
        stream.seek(self.header.position)
        self.data = decompress(stream.read(self.header.archived_size))


class GRF:

    def __init__(self, stream):
        self.stream = stream
        self.header = parse_header(self.stream)
        self.index = parse_index(self.stream, self.header)

    def __enter__(self):
        return self

    def __exit__(self, *args):
        pass

    def get(self, filename):
        """get a file from the archive"""
        return GRFFile(filename, self.stream, self.index[filename])

    def extract(self, filename, parent_dir=None):
        grf_file = self.get(filename)
        file_path = os.path.join(*filename.split('\\'))
        if parent_dir:
            file_path = os.path.join(parent_dir, file_path)
        if not os.path.exists(os.path.dirname(file_path)):
            os.makedirs(os.path.dirname(file_path))
        with open(file_path, 'wb') as extracted_file:
            extracted_file.write(grf_file.data)
