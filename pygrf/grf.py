import os
from io import BytesIO
from struct import unpack
from zlib import decompress
from functools import partial
from itertools import takewhile
from contextlib import suppress
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
    # try with each known encoding
    for encoding in ENCODINGS:
        with suppress(UnicodeDecodeError):
            return name.decode(encoding)
    # upon failure, replace failed characters with their hex representation
    name = name.decode(errors='backslashreplace')
    name = name.replace('\\x', '')
    return name


def parse_name(name):
    """parse the raw filename data into a usable filename"""
    # split the name into its path parts
    path = name.split(b'\\')

    # remove from the beginning
    if path[0] == b'data':
        path.pop(0)

    # decode each part
    path = [decode_name(part) for part in path]

    # rejoin the path with appropriate path separators
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


class GRFFile(BytesIO):

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
            self.data = decompress(stream.read(self.header.archived_size))
        super().__init__(self.data)


class Index:
    """
    GRF Index
    =========

    The index of the GRF archive is stored in a zlib compressed blob at the
    offset found in the header. The first four bytes are the compressed size of
    the index, followed by four bytes for the real size. These are 32 bit
    unsigned integers stored in little endian byte order. After the first eight
    bytes begins the compressed data.

    The decompressed data is a simple series of filenames followed by the file
    header. The filenames are simple null-terminated C strings. The file header
    is the next 17 bytes.
    """

    def __init__(self, stream, header):
        """create an index for the grf archive

        :param stream: the byte stream of the entire grf file
        :param header: the grf header information
        """
        # decompress the real file list data
        stream.seek(header.index_offset)
        compressed_length, real_length = unpack('<II', stream.read(8))
        self.data = BytesIO(decompress(stream.read(compressed_length)))

        self.file_count = header.file_count
        self.files = {}

    def __getitem__(self, filename):
        # if the file is already indexed, return it
        with suppress(KeyError):
            return self.files[filename]

        # parse more files until the desired file is found
        while True:
            try:
                next_file, header = self._pop()
            except StopIteration:
                break
            if next_file == filename:
                return header

        # raise a key error if the file cannot be found
        raise KeyError()

    def __contains__(self, filename):
        try:
            self[filename]
        except KeyError:
            return False
        return True

    def __len__(self):
        return self.file_count

    def __iter__(self):
        self.files_iterator = iter(self.files.items())
        return self

    def __next__(self):
        # get the next already parsed file
        with suppress(StopIteration):
            return next(self.files_iterator)

        # pop files until the end is reached
        # _pop() will raise a StopIteration on its own
        return self._pop()

    def _pop_filename(self):
        """pop the next filename from the data stream"""
        # read bytes until a null terminator or EOF is found
        read_name = iter(partial(self.data.read, 1), b'\x00')
        read_name = takewhile(lambda c: c != b'', read_name)
        return b''.join(read_name)

    def _pop(self):
        """pop the next filename and header

        This will read the next filename and header, store them inside the
        known files dictionary, and return both parts

        :returns: filename, header
        :raises StopIteration: no more data to parse
        """
        # pop the filename. if the filename is empty, EOF has been reached
        filename = self._pop_filename()
        if filename == b'':
            raise StopIteration

        # parse the filename
        filename = parse_name(filename)

        # pop the header data
        header = self.data.read(FILE_HEADER_LENGTH)

        # add the file to the index and return it
        self.files[filename] = header
        return filename, header


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
        self.index_iter = iter(self.index)
        return self

    def __next__(self):
        # pop the next file in the index and open it by name
        filename, header = next(self.index_iter)
        return self.open(filename)

    def __len__(self):
        return self.header.file_count

    def open(self, filename):
        """open a file from the archive"""
        try:
            header = self.index[filename]
        except KeyError:
            raise FileNotFoundError(filename)
        return GRFFile(filename, header, self.stream)

    def extract(self, filename, parent_dir=None):
        grf_file = self.open(filename)
        file_path = os.path.join(*filename.split('\\'))
        if parent_dir:
            file_path = os.path.join(parent_dir, file_path)
        if not os.path.exists(os.path.dirname(file_path)):
            os.makedirs(os.path.dirname(file_path))
        with open(file_path, 'wb') as extracted_file:
            extracted_file.write(grf_file.data)

    def close(self):
        self.stream.close()
