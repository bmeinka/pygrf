import collections
import io
import itertools
import struct
from .exceptions import FileParseError


SUPPORTED_VERSIONS = (0x100, 0x101, 0x200, 0x201)


Header = collections.namedtuple('Header', ('version', 'pal_count', 'rgb_count'))
Color = collections.namedtuple('Color', ('r', 'g', 'b', 'a'))


class Image:

    def __init__(self, w, h, px):
        self.w, self.h, self.px = w, h, px

    @property
    def bytes(self):
        """ the raw bytes data for this images pixels """
        return bytes(itertools.chain.from_iterable(self.px))


def parse_header(stream):
    """
    Parse the header of a SPR file

    :param stream: the stream for the file

    The spr header varies in length between 6 and 8 bytes, depending on the version. RGB
    format image support was added in version 0x200, which adds a count for RGB images to
    the header (an additional two bytes). The header has the following information:

    - a 2-byte signature containing b'SP'
    - a 2-byte integer containing the version number (0x100, 0x101, 0x200, 0x201)
    - a 2-byte integer containing the palette image count
    - a 2-byte integer containing the RGB image count (version 0x200+)
    """
    # start at the beginning and read as we go
    stream.seek(0)

    # verify the signature
    signature = stream.read(2)
    if signature != b'SP':
        raise FileParseError('invalid signature')

    # verify the version number
    version, = struct.unpack('<H', stream.read(2))
    if not version in SUPPORTED_VERSIONS:
        raise FileParseError('unsuppported version')

    # get the palette image count
    pal_count, = struct.unpack('<H', stream.read(2))

    # get the rgb image count. If the version is less than 0x200, it must be zero
    if version < 0x200:
        rgb_count = 0
    else:
        rgb_count, = struct.unpack('<H', stream.read(2))

    return Header(version, pal_count, rgb_count)


def parse_palette(stream):
    """
    Parse the color palette for the given SPR file

    :param stream: the SPR file to parse the palette from

    The last 1024 bytes of a SPR image is its palette. The palette is a series of 256 RGBA
    colors. The alpha channel is ignored. The first color is the background color, and
    should be treated as transparent. All other colors are fully opaque (alpha 255).
    """
    # the palette is at the end of the file, so seek to it
    stream.seek(-1024, 2)
    def parse_color(i):
        """ parse a color, making sure only the background color is transparent """
        r, g, b, a = struct.unpack('BBBB', stream.read(4))
        a = 255 if i > 0 else 0
        return Color(r, g, b, a)
    colors = [parse_color(i) for i in range(256)]
    return colors


def unpack_rle(px):
    """
    Unpack RLE data

    :param px: the RLE data

    If an index is zero, the next index tells us how many zeroes there should be in a row
    starting at that position.
    """
    out = []
    i = 0
    while i < len(px):
        if px[i] == 0:
            # go to the next pixel and add its value in zeroes to the output data
            i += 1
            out += [0] * px[i]
        else:
            out.append(px[i])
        i += 1
    return out


def parse_pal_images(stream):
    """
    Parse PAL images in the SPR file

    :param stream: the SPR file to parse PAL images from

    PAL images come in two different formats, depending on the version of the SPR file.
    Normal PAL images are a simple list of indexes in the color palette. Version 0x201
    introduced PAL-RLE, which have run-length encoded backgrounds.
    """
    # determine if we should be handling run-length encoded images
    rle = False if stream.version < 0x201 else True

    def parse_image():
        # get the total size of the image data stored in file
        w, h = struct.unpack('<HH', stream.read(4))
        size = w * h
        if rle:
            size, = struct.unpack('<H', stream.read(2))

        # read the pixel data
        px = stream.read(size)

        # unpack rle encoded pixel data
        if rle:
            px = unpack_rle(px)

        # create a flat array of color channels, e.g. r, g, b, a, r, g, b, a ...
        pixels = itertools.chain.from_iterable(stream.palette[i] for i in px)

        # pack the rows of the flat array
        pixels = tuple(tuple(itertools.islice(pixels, w * 4)) for _ in range(h))

        return Image(w, h, pixels)

    return [parse_image() for _ in range(stream.header.pal_count)]


def parse_rgb_images(stream):
    """
    Parse RGB images in the SPR file

    :param stream: the SPR file to parse RGB images from
    """
    def parse_image():
        # read the image from the stream
        w, h = struct.unpack('<HH', stream.read(4))
        px = stream.read(4 * w * h)

        pixels = [tuple(itertools.islice(px, w * 4)) for _ in range(h)]
        pixels = tuple(reversed(pixels))

        return Image(w, h, pixels)

    return [parse_image() for _ in range(stream.header.rgb_count)]


def parse_images(stream):
    """
    Parse the images in the SPR file

    :param stream: the spr file stream
    :returns: list of images with PAL first and RGB after

    The list of images should contain images with the following infromation:

    - w: the width of the image in pixels
    - h: the height of the image in pixels
    - px: the array of pixel data

    The pixel data will have boxed rows and flat pixels. The arrangement will look
    something like this:

        ((r, g, b, a, r, g, b, a, r, g, b, a),
         (r, g, b, a, r, g, b, a, r, g, b, a),
         (r, g, b, a, r, g, b, a, r, g, b, a))
    """
    # ensure the stream is in the correct position
    stream.seek(6 if stream.version < 0x200 else 8)

    pal = parse_pal_images(stream)
    rgb = parse_rgb_images(stream)
    return pal + rgb


class SPR(io.BytesIO):

    def __init__(self, stream):
        """parse a spr file from the given stream"""
        # read the entire data stream and use its data as our own
        stream.seek(0)
        super().__init__(stream.read())

        self.header = parse_header(self)
        self.palette = parse_palette(self)
        self.images = parse_images(self)

        # reset the stream to zero
        self.seek(0)

    @property
    def version(self):
        return self.header.version

    @property
    def image_count(self):
        return self.header.pal_count + self.header.rgb_count
