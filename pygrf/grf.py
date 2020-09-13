import collections
import contextlib
import functools
import io
import itertools
import os
import struct
import zlib
from . import filetypes
from .exceptions import GRFParseError


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


Header = collections.namedtuple('GRFHeader', (
    'allow_encryption', 'index_offset', 'file_count', 'version'
))


FileHeader = collections.namedtuple('GRFFileHeader', (
    'compressed_size', 'archived_size', 'real_size', 'flag', 'position'
))


def decode_name(name):
    """decode a name using multiple encodings"""
    # try with each known encoding
    for encoding in ENCODINGS:
        with contextlib.suppress(UnicodeDecodeError):
            return name.decode(encoding)
    # upon failure, replace failed characters with their hex representation
    name = name.decode(errors='backslashreplace')
    name = name.replace('\\x', '')
    return name


def parse_name(name):
    """parse the raw filename data into a usable filename"""
    # split the name into its path parts
    path = name.split(b'\\')

    # remove 'data' from the beginning
    if path[0] == b'data':
        path.pop(0)

    path = [decode_name(part) for part in path]
    return os.path.join(*path)


def parse_header(stream):
    """parse the grf header

    :param stream: a byte stream of the grf file

    The header portion of the GRF archive is the first 46 bytes. They are
    arranged as follows:

    ======  ====  =======================================
    offset  size  purpose
    ======  ====  =======================================
    0       15    "Master of Magic" signature
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
    include the 46 byte header, but the parsed value does.

    File Count
    ==========

    The file count is stored in two different integers. The first one is
    subtracted from the second, and 7 is taken away to get the total number
    of files stored in the archive.

    Version
    =======

    The version is stored in two bytes. The first byte represents the major
    version number and the second byte is the minor version number. The minor
    version number is ignored by this parser. Currently, the only supported
    version is `0x0200`.
    """
    ENCRYPTION_FLAGS = {bytes(range(15)): True, bytes([0] * 15): False}

    SIGNATURE = slice(0, 15)
    ENCRYPTION = slice(15, 30)
    OFFSET = slice(30, 34)
    FILECOUNT = slice(34, 42)
    VERSION = slice(42, 46)

    # read the full header data
    stream.seek(HEADER_OFFSET)
    data = stream.read(HEADER_LENGTH)

    # verify the signature is valid
    if not data[SIGNATURE] == b'Master of Magic':
        raise GRFParseError('missing signature')

    # verify the encryption flag is valid
    try:
        encryption = ENCRYPTION_FLAGS[data[ENCRYPTION]]
    except KeyError:
        raise GRFParseError('invalid encryption flag')

    # get the position of the file list
    offset, = struct.unpack('<I', data[OFFSET])
    offset += HEADER_LENGTH

    # get the number of files
    b, a = struct.unpack('<II', data[FILECOUNT])
    file_count = a - b - 7
    if file_count < 0:
        raise GRFParseError('invalid file count')

    # get the version
    version, = struct.unpack('<I', data[VERSION])
    version &= 0xff00  # ignore minor version information
    if version not in SUPPORTED_VERSIONS:
        raise GRFParseError('unsupported version')

    return Header(encryption, offset, file_count, version)


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

    The flag byte stores information about the file and how it is stored
    within the archive. The flags are:

    =====  =================================================
    value  purpose
    =====  =================================================
    0x1    if set, this is a file. if not, it is a directory
    0x2    set if the file uses mixed encryption
    0x4    set if only the first 0x14 bytes are encrypted
    =====  =================================================

    Position
    ========

    This is the offset at which the file is stored in the archive. The stored
    value does not include the 46 byte header. The parsed value does.
    """
    SIZES = slice(0, 12)
    FLAG = 12
    POSITION = slice(13, 17)

    compressed, archived, real = struct.unpack('<III', data[SIZES])
    flag = data[FLAG]
    position, = struct.unpack('<I', data[POSITION])
    position += HEADER_LENGTH

    return FileHeader(compressed, archived, real, flag, position)


class GRFFile(io.BytesIO):

    def __init__(self, filename, header_data, stream):
        """fetch file from grf archive

        :param filename: the filename of the file
        :param header_data: the header data for this file
        :param stream: the grf data stream
        """
        self.filename = filename
        self.header = parse_file_header(header_data)

        # seek to, read and decompress file data
        stream.seek(self.header.position)
        if self.header.real_size == 0:
            self.data = b''
        else:
            self.data = zlib.decompress(stream.read(self.header.archived_size))
        super().__init__(self.data)

    def __eq__(self, other):
        return other.filename == self.filename and other.data == self.data


class Index:
    """
    GRF Index
    =========

    The index of the GRF archive is found at the offset in the header. The
    index has a small header that is arranged as follows:

    ======  ====  ===============
    offset  size  purpose
    ======  ====  ===============
    0       4     compressed size
    4       4     real size
    ======  ====  ===============

    These values are stored as 32-bit little endian integers. After the
    header begins the actual index data. The data is zlib compressed. Once
    decompressed, the data is a series of files. Each file is stored in this
    way:

    - a null-terminated C string containing the filename
    - a 17 byte file header
    """
    def __init__(self, stream, header):
        """create an index for the grf archive

        :param stream: the byte stream of the grf file
        :param header: the grf header
        """
        # decompress the raw file list
        stream.seek(header.index_offset)
        compressed_length, _ = struct.unpack('<II', stream.read(8))
        self.data = io.BytesIO(zlib.decompress(stream.read(compressed_length)))

        # cache the filenames and headers as they are indexed
        self.indexed = {}

    def __getitem__(self, filename):
        """get the header for the given filename"""
        # if the file is already indexed, return it
        with contextlib.suppress(KeyError):
            return self.indexed[filename]

        # parse more files until the desired file is found
        while True:
            try:
                next_file = self.parse_next()
            except EOFError:
                break
            if next_file == filename:
                return self.indexed[filename]

        # the file wasn't found yet
        raise KeyError

    def __iter__(self):
        """all the filenames in the index"""
        yield from self.indexed
        while True:
            try:
                yield self.parse_next()
            except EOFError:
                break

    def parse_next(self):
        """parse the next filename and store its header"""
        # read bytes until a null terminator or EOF is found
        read_name = iter(functools.partial(self.data.read, 1), b'\x00')
        read_name = itertools.takewhile(lambda c: c != b'', read_name)
        filename = b''.join(read_name)

        # if EOF was reached, stop looking for more files
        if filename == b'': # is this the best way to determine EOF?
            raise EOFError

        filename = parse_name(filename)
        header = self.data.read(FILE_HEADER_LENGTH)

        # index the file header and return the filename
        self.indexed[filename] = header
        return filename


class GRF:

    def __init__(self, stream):
        self.stream = stream
        self.header = parse_header(self.stream)
        self.index = Index(self.stream, self.header)

    def __enter__(self):
        return self

    def __exit__(self, *args):
        self.close()

    def __iter__(self):
        """iterate over files in the archive"""
        for filename in self.index:
            yield self.open(filename)

    def __len__(self):
        """the number of files in the grf archive"""
        return self.header.file_count

    @property
    def version(self):
        """the vesion number for the grf archive"""
        return self.header.version

    @property
    def allow_encryption(self):
        """whether or not the grf archive allows encrypted files"""
        return self.header.allow_encryption

    def files(self):
        """all the names of the files contained in the archive"""
        yield from self.index

    def open(self, filename):
        """open a file in the archive"""
        try:
            header = self.index[filename]
        except KeyError:
            raise FileNotFoundError(filename)
        opened_file = GRFFile(filename, header, self.stream)
        return filetypes.parse(opened_file)

    def extract(self, filename, parent_dir=None):
        """extract a file from the archive to the filesystem

        :param filename: the name of the file to extract
        :param parent_dir: the parent directory to store the file in
        """
        # get the file data to extract
        grf_file = self.open(filename)

        # get the target path
        path = os.path.join('data', *filename.split(os.path.sep))
        if parent_dir and os.path.isdir(parent_dir):
            path = os.path.join(parent_dir, path)

        # make sure the directory exists
        if not os.path.exists(os.path.dirname(path)):
            os.makedirs(os.path.dirname(path))

        # create the file and write the data
        grf_file.seek(0)
        with open(path, 'wb') as extracted_file:
            extracted_file.write(grf_file.read())

    def close(self):
        """close the archive"""
        self.stream.close()
