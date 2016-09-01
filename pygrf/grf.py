import struct


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


class GRFArchive:

    def __init__(self, filename):
        self.file = open(filename, 'rb')
        self.header = GRFHeader(self.file)

    def __enter__(self):
        return self

    def __exit__(self, *args):
        pass
