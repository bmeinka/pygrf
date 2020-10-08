""" spr file parsing """
import struct
from typing import Tuple, Sequence
from itertools import chain
from .exceptions import FileParseError
from .graphics import Image, Color
from .filetypes import parse_header, Header


color_struct = struct.Struct('<3Bx')


class SprParser:
    """ base sprite file parser class """

    count_struct = struct.Struct('')

    def __init__(self, header: Header, data: bytes):
        """ create a new spr parser that parses the given data """
        self.header = header
        self.data = data
        self.palette = None

    @property
    def count(self) -> int:
        """ the number of images contained in the file """
        return sum(self.parse_count())

    @property
    def pal_count(self) -> int:
        """ the number of pal images """
        return self.parse_count()[0]

    @property
    def rgb_count(self) -> int:
        """ the number of rgb images """
        return self.parse_count()[1]

    @property
    def offset(self):
        """ the position in data where the images begin """
        return self.header.size + self.count_struct.size

    def parse_count(self) -> Tuple[int, int]:
        """ parse the counts from file """
        raise NotImplementedError

    def parse_palette(self):
        """ parse an embedded palette """
        raise NotImplementedError

    def parse_pal(self, offset) -> Image:
        """ parse the pal image found at the offset """
        raise NotImplementedError

    def parse_rgb(self, offset) -> Image:
        """ parse the rgb image found at the offset """
        raise NotImplementedError

    def pal_size(self, offset) -> int:
        """ get the size of a pal image at the given offset """
        raise NotImplementedError

    def rgb_size(self, offset) -> int:
        """ get the size of an rgb image at the given offset """
        raise NotImplementedError

    def pal_offset(self, index) -> int:
        """ get the offset of a pal image """
        offset = self.offset
        for _ in range(index):
            offset += self.pal_size(offset)
        return offset

    def rgb_offset(self, index) -> int:
        """ get the offset of an rgb image

        index does *NOT* include the pal images. index 0 is the first rgb image
        """
        offset = self.pal_offset(self.pal_count)
        for _ in range(index):
            offset += self.rgb_size(offset)
        return offset

    def get_palette(self) -> Sequence[Color]:
        """ get the palette for pal image parsing """
        if self.palette is None:
            return self.parse_palette()
        return self.palette

    def get_image(self, index) -> Image:
        """ get an image """
        pal = self.pal_count
        if index < pal and self.get_palette() is None:
            raise FileParseError('unable to parse pal images with no palette')
        if index < pal:
            return self.parse_pal(self.pal_offset(index))
        index -= pal
        return self.parse_rgb(self.rgb_offset(index))


class Spr100(SprParser):
    """ the base version of the SPR format """

    count_struct = struct.Struct('<H')
    pal_struct = struct.Struct('<2H')

    def parse_count(self):
        count, = self.count_struct.unpack_from(self.data, self.header.size)
        return (count, 0)

    def parse_palette(self):
        return None

    def pal_size(self, offset):
        width, height = self.pal_struct.unpack_from(self.data, offset)
        return (width * height) + self.pal_struct.size

    def parse_pal(self, offset):
        width, height = self.pal_struct.unpack_from(self.data, offset)
        palette = self.get_palette()
        start = offset + self.pal_struct.size
        stop = start + (width * height)
        pixels = [palette[i] for i in self.data[start:stop]]
        return Image(width, height, pixels)

    def rgb_size(self, offset):
        raise FileParseError('rgb images unsupported')

    def parse_rgb(self, offset):
        raise FileParseError('rgb images unsupported')


class Spr101(Spr100):
    """ adds an embedded palette to the end of the file """

    def parse_palette(self):
        palette = color_struct.iter_unpack(self.data[-1024:])
        palette = [Color(*color, 255) for color in palette]
        # make the background (index 0) transparent
        palette[0] = palette[0]._replace(a=0)
        return palette


class Spr200(Spr101):
    """ adds support for RGB images """

    count_struct = struct.Struct('<2H')
    rgb_struct = struct.Struct('<2H')

    def parse_count(self):
        return self.count_struct.unpack_from(self.data, self.header.size)

    def rgb_size(self, offset):
        width, height = self.rgb_struct.unpack_from(self.data, offset)
        return (width * height * 4) + self.rgb_struct.size

    def parse_rgb(self, offset):
        # get the dimensions of the image
        width, height = self.rgb_struct.unpack_from(self.data, offset)

        # get the pixel data as color objects
        start = offset + self.rgb_struct.size
        stop = start + (width * height * 4)
        pixels = struct.iter_unpack('<I', self.data[start:stop])
        pixels = [Color.from_rgba32(color[0]) for color in pixels]

        # flip the image
        pixels = [pixels[row * width:(row * width) + width]
                  for row in range(height)]
        pixels = list(chain.from_iterable(reversed(pixels)))

        return Image(width, height, pixels)


class Spr201(Spr200):
    """ adds background RLE to PAL images """

    pal_struct = struct.Struct('<3H')

    def pal_size(self, offset):
        _, _, size = self.pal_struct.unpack_from(self.data, offset)
        return self.pal_struct.size + size

    def parse_pal(self, offset):
        width, height, size = self.pal_struct.unpack_from(self.data, offset)
        palette = self.get_palette()

        start = offset + self.pal_struct.size
        stop = start + size

        pixels = [palette[i] for i in _unpack_rle(self.data[start:stop])]

        return Image(width, height, pixels)


class SPR:
    """ a container for sprite images """

    def __init__(self, data: bytes):
        self.header = parse_header(data, b'SP')
        self.parser = _get_parser(data, self.header)

    def __len__(self) -> int:
        return self.parser.count

    def __getitem__(self, index) -> Image:
        if not isinstance(index, int):
            raise IndexError
        length = len(self)
        if index < 0:
            # index is already negative, so add it instead of subtract
            index = length + index
        if index < 0 or index >= length:
            raise IndexError
        return self.parser.get_image(index)

    @property
    def version(self) -> int:
        """ the version of the spr file """
        return self.header.version


def _get_parser(data: bytes, header: Header) -> SprParser:
    """ get the appropriate parser object based on the file version """
    parsers = {
        0x100: Spr100,
        0x101: Spr101,
        0x200: Spr200,
        0x201: Spr201,
    }
    if header.version not in parsers:
        raise FileParseError('unsupported version')
    return parsers[header.version](header, data)


def _unpack_rle(data: bytes) -> bytes:
    """ unpack run-length encoded data """
    out = []
    index = 0
    while index < len(data):
        if data[index] == 0:
            index += 1
            out += [0] * data[index]
        else:
            out.append(data[index])
        index += 1
    return out
