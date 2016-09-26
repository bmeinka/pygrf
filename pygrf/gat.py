import collections
import functools
import io
import struct

from .exceptions import InvalidGATError


HEADER_LENGTH = 14
TILE_LENGTH = 20


Header = collections.namedtuple('GATHeader', ('width', 'height'))
Tile = collections.namedtuple('Tile', (
    'bottom_left', 'bottom_right', 'top_left', 'top_right', 'type', 'altitude'
))


def parse_header(stream):
    """parse the header of a gat file

    :param stream: the stream of the gat file
    :returns: (width, height)

    The gat header is a simple 14 bytes long. It contains three pieces of information:

    - a 6-byte signature containing b'GRAT\x01\x02'
    - a 4-byte integer containing the gat width
    - a 4-byte integer containing the gat height

    All integers are in little-endian byte order.
    """
    SIGNATURE = slice(0, 6)
    SIZE = slice(6, 14)

    # read the entire header content
    stream.seek(0)
    header_data = stream.read(HEADER_LENGTH)

    # verify the signature
    if header_data[SIGNATURE] != b'GRAT\x01\x02':
        raise InvalidGATError('invalid signature')

    # unpack the sizes and return them
    return Header(*struct.unpack('<II', header_data[SIZE]))


def split_tiles(stream):
    """split the list of tiles into individual tiles
    
    :param stream: the source stream to read from
    :returns: a list of 20-byte chunks
    """
    # start at the end of the header
    stream.seek(HEADER_LENGTH)

    # read 20-bytes at a time until EOF
    return list(iter(functools.partial(stream.read, 20), b''))


def parse_tile(data):
    """parse the tile represented by the data

    :param data: the 20-byte data for the tile
    :returns: a Tile

    Each tile is made from 20 bytes of data. The data is as follows, and all values are in
    little-endian byte order:

    ======  ====  =====  ====================
    offset  size  type   purpose
    ======  ====  =====  ====================
    0       4     float  bottom left altitude
    4       4     float  bottom right altitude
    8       4     float  top left altitude
    12      4     float  top right altitude
    16      4     int    type flag
    ======  ====  =====  ====================

    The heights are all floats. The heights are inverted, so negative numbers result in higher
    altitude. This is inverted by the parser to make more logical sense.

    The type flag determines how the tile interacts with the world. The flag is interpreted
    differently depending on the height of the tile and the map water level. Tiles that are
    underwater act differently than tiles that are above water.

    Above Water Types
    -----------------

    - 0: walkable
    - 1: non-walkable
    - 2: non-walkable, non-snipable water
    - 3: walkable water
    - 4: non-walkable, snipable water
    - 5: snipable cliff
    - 6: non-snipable cliff

    Below Water Types
    -----------------

    - 0: walkable water
    - 1: non-walkable, non-snipable water
    - 3: walkable water
    - 5: non-walkable, snipable water
    - 6: non-walkable, non-snipable water
    """
    values = struct.unpack('<ffffI', data)
    heights, type_flag = values[:4], values[4]
    # invert the heights, which are stored on a negative scale
    heights = [height * -1 for height in heights]
    # the altitude is the average of all the heights
    altitude = sum(heights) / len(heights)
    return Tile(*heights, type_flag, altitude)


class GAT(io.BytesIO):

    def __init__(self, stream):
        """parse a gat file from the given stream"""
        # read the entire data stream and use its data as our own
        stream.seek(0)
        super().__init__(stream.read())

        self.header = parse_header(self)
        self.tile_data = split_tiles(self)

        # make sure the number of tiles is correct
        if len(self.tile_data) != (self.width * self.height):
            raise InvalidGATError('invalid tile count')
        # make sure the last tile has a correct length
        if len(self.tile_data[-1]) != TILE_LENGTH:
            raise InvalidGATError('invalid tile length')
        self.tiles = {}

        # reset the stream to 0, as if the stream was just opened
        self.seek(0)

    def __getitem__(self, coordinates):
        x, y = coordinates
        # make sure the coordinates are within bounds
        if x >= self.width or y >= self.height or x < 0 or y < 0:
            raise IndexError
        if not (x, y) in self.tiles:
            tile_data = self.tile_data[y + x * self.width]
            self.tiles[(x, y)] = parse_tile(tile_data)
        return self.tiles[(x, y)]

    @property
    def width(self):
        return self.header.width

    @property
    def height(self):
        return self.header.height

    @property
    def size(self):
        return (self.width, self.height)
