import zlib
import struct


ENCODINGS = ['euc_kr', 'johab', 'uhc', 'mskanji']


class GRFHeader:
    '''
    A GRF Header
    ############

    The header portion of the GRF archive is the first 46 bytes. They are
    arranged as follows:

    ======  ====  =======================================
    offset  size  purpose
    ======  ====  =======================================
    0       15    A watermark that says 'Master of Magic'
    15      15    An encryption flag
    30      4     The offset where the file list is found
    34      8     A count of the number of files
    42      4     The version number
    ======  ====  =======================================

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

    The offset is where in the file the list of files is found. The stored value
    does not include the 46 byte header. This is stored in a little endian 32
    bit unsigned integer.

    File Count
    ==========

    The file count is stored in two different 32 bit unsigned integers. The
    first value is subtracted from the second, and then 7 is taken away to get
    the actual file count.

    .. TODO:: figure out what these two different values actually mean

    Version
    =======

    The version is stored in two bytes. The first byte represents the major
    version number and the second byte is the minor version number. The minor
    version number is ignored by this parser. Currently, the only supported
    version is `0x0200`.
    '''
    SUPPORTED_VERSIONS = [0x0200]

    HEADER_LENGTH = 46
    HEADER_OFFSET = 0

    WATERMARK = b'Master of Magic'
    ENCRYPTION_ALLOW = bytes(range(15))
    ENCRYPTION_DENY = bytes([0] * 15)

    WATERMARK_SLICE = slice(0, 15)
    ENCRYPTION_SLICE = slice(15, 30)
    OFFSET_SLICE = slice(30, 34)
    FILECOUNT_SLICE = slice(34, 42)
    VERSION_SLICE = slice(42, 46)

    def __init__(self, grf_file):
        # read the full header data
        grf_file.seek(self.HEADER_OFFSET)
        self.data = grf_file.read(self.HEADER_LENGTH)

        # verify the watermark is valid
        watermark = self.data[self.WATERMARK_SLICE]
        if not watermark == self.WATERMARK:
            raise ValueError('Invalid GRF Header: missing Master of Magic')

        # determine encryption
        encrypt_flag = self.data[self.ENCRYPTION_SLICE]
        if encrypt_flag == self.ENCRYPTION_ALLOW:
            self.allow_encryption = True
        elif encrypt_flag == self.ENCRYPTION_DENY:
            self.allow_encryption = False
        else:
            raise ValueError('Invalid GRF Header: invalid encryption flag')

        # get the position of the filelist
        offset, = struct.unpack('<I', self.data[self.OFFSET_SLICE])
        self.entry_point = self.HEADER_LENGTH + offset

        # get the number of files
        b, a = struct.unpack('<II', self.data[self.FILECOUNT_SLICE])
        self.file_count = a - b - 7
        if self.file_count < 0:
            raise ValueError('Invalid GRF Header: invalid file count')

        # get the version
        self.version, = struct.unpack('<I', self.data[self.VERSION_SLICE])
        self.version &= 0xFF00 # ignore minor version information
        if self.version not in self.SUPPORTED_VERSIONS:
            raise ValueError('Invalid GRF File: unsupported version')


class GRFFile:
    '''
    GRF File
    ########

    The metadata about a file held inside a GRF archive. This data is stored
    with the filename string followed by 17 additional bytes arranged in the
    following way:

    ======  ====  ===============
    offset  size  purpose
    ======  ====  ===============
    0       4     compressed size
    4       4     size in file
    8       4     real size
    12      1     flags
    13      4     position
    ======  ====  ===============

    All integers are stored in little endian byte order.

    Compressed Size
    ===============

    Files stored in the GRF archive are compressed. This is the size of the
    compressed data.

    Size in File
    ============

    Some files stored in the GRF archive are encrypted or otherwise manipulated.
    This is the size of the data within the actual GRF file.

    Real Size
    =========

    This is the size of the file after it has been decompressed.

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

    Position
    ========

    This is the offset at which the file is stored in the GRF archive. The
    stored value does not include the 46 byte header, which will be appended.
    '''
    FILE_INFO_SIZE = 0x11

    SIZE_SLICE = slice(0, 12)
    FLAG_SLICE = 12 # not actually a slice because only one byte
    POSITION_SLICE = slice(13, 17)

    # flags
    IS_FILE = 0x01

    def __init__(self, file_info):
        # pop the filename off and store it
        filename, file_info = file_info.split(b'\x00', 1)
        self.filename = decode_name(filename)

        # read size and position information
        sizes = struct.unpack('<III', file_info[self.SIZE_SLICE])
        self.compressed_size, self.archived_size, self.real_size = sizes
        self.position, = struct.unpack('<I', file_info[self.POSITION_SLICE])

        # read the flags
        self.flags = file_info[self.FLAG_SLICE]

    @property
    def is_file(self):
        return self.flags & self.IS_FILE == self.IS_FILE

    @property
    def is_dir(self):
        return not self.is_file


def decode_name(name):
    for encoding in ENCODINGS:
        try:
            return name.decode(encoding)
        except UnicodeDecodeError as err:
            pass
    raise UnicodeError(name)


def parse_file_list(grf_file, header):
    '''parse the list of files

    :param grf_file: the IO stream to read the list from
    :param header: the GRF header with appropriate offset information
    :returns: list of GRF Files
    '''
    # seek to and read size information
    grf_file.seek(header.entry_point)
    compressed_length, real_length = struct.unpack('<II', grf_file.read(8))

    # read and decompress the file list data
    file_list = grf_file.read(compressed_length)
    file_list = zlib.decompress(file_list)

    # parse each file
    files = {}
    for _ in range(header.file_count):
        filename, _ = file_list.split(b'\x00', 1)
        files[decode_name(filename)] = GRFFile(file_list)

        # move ahead to the next file
        size = len(filename) + GRFFile.FILE_INFO_SIZE + 1
        file_list = file_list[size:]

    return files


class GRFArchive:

    def __init__(self, filename):
        self.file = open(filename, 'rb')
        self.header = GRFHeader(self.file)
        self.files = parse_file_list(self.file, self.header)

    def __enter__(self):
        return self

    def __exit__(self, *args):
        pass
