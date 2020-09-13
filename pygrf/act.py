import collections
import contextlib
import io
import struct
from .exceptions import FileParseError
from .util import get_version


SUPPORTED_VERSIONS = (0x200, 0x201, 0x202, 0x203, 0x204, 0x205)


class Sprite:

    def __init__(self, x, y, index, flags):
        # get the things that exist for every sprite from file
        self.x, self.y, self.index, self.flags = x, y, index, flags

        # set the defaults to be used before the feature is supported in the parsed
        # version. these will be altered afterward when the values are parsed
        self.color = (255, 255, 255, 255)
        self.zoom = (1.0, 1.0)
        self.angle = 0.0
        self.type = 'pal'
        # before 0x205, we don't know the width and height, so they are set to None
        self.size = None

    @property
    def flipped(self):
        return self.flags & 1 == 1

    def __eq__(self, other):
        return (self.index == other.index and
                self.x == other.x and self.y == other.y and
                self.flags == other.flags and
                self.color == other.color and
                self.zoom == other.zoom and
                self.angle == other.angle and
                self.size == other.size)


def parse_sprite(stream):
    """
    """
    # get the x, y offsets, the spr index and rendering flags
    out = Sprite(*struct.unpack('<4i', stream.read(16)))

    # 0x200 added color
    if stream.version >= 0x200:
        out.color = struct.unpack('BBBB', stream.read(4))

    # 0x200 added zoom
    # zoom is a float in version 0x200 to 0x203, and split between x and y in 0x204+
    if stream.version >= 0x200 and stream.version <= 0x203:
        zoom, = struct.unpack('<f', stream.read(4))
        out.zoom = (zoom, zoom)
    elif stream.version >= 0x204:
        out.zoom = struct.unpack('<ff', stream.read(8))

    # 0x200 added rotation
    if stream.version >= 0x200:
        out.angle, = struct.unpack('<f', stream.read(4))

    # 0x200 added image type (rgb or pal)
    if stream.version >= 0x200:
        image_type, = struct.unpack('<i', stream.read(4))
        if image_type:
            out.type = 'rgb'

    # 0x205 added width and height (I don't see the point?)
    if stream.version >= 0x205:
        out.size = struct.unpack('<ii', stream.read(8))

    return out


class Frame:

    def __init__(self, range1, range2, sprites):
        self.range1, self.range2, self.sprites  = range1, range2, sprites

        # set the defaults
        self.event_id = -1
        self.attach_points = tuple()

    def __eq__(self, other):
        return self.sprites == other.sprites


def parse_frame(stream):
    """
    """
    # get the ranges (don't know what they are for yet)
    ranges = struct.unpack('<8i', stream.read(32))
    range1, range2 = ranges[:4], ranges[4:]

    # get the sprite count (no idea why it wouldn't be one
    sprite_count, = struct.unpack('<i', stream.read(4))
    sprites = tuple(parse_sprite(stream) for _ in range(sprite_count))

    out = Frame(range1, range2, sprites)

    # get the event id (default is -1)
    if stream.version >= 0x200:
        out.event_id, = struct.unpack('<i', stream.read(4))

    # get the attach points
    if stream.version >= 0x203:
        ap_count, = struct.unpack('<i', stream.read(4))
        out.attach_points = tuple(struct.unpack('<4i', stream.read(16))
                                  for _ in range(ap_count))

    return out


class Action:

    def __init__(self, frames):
        self.frames = frames
        self.delay = 4.0

    def __eq__(self, other):
        return (self.frames == other.frames and
                self.delay == other.delay)

def parse_actions(stream):
    """
    Parse the list of actions in the ACT file

    :param stream: the act file to parse

    The header of the action list starts with a uint16 containing the action count. After
    that is a 10-byte piece of data. I have no idea what it does or what it is for.
    """
    stream.seek(4)
    count, = struct.unpack('<H', stream.read(2))

    # skip ten bytes
    stream.read(10)

    def parse_action():
        """
        An action is really just a list of animations. The action starts with a 32-bit
        integer count of animations followed by a list of animations.
        """
        frame_count, = struct.unpack('<i', stream.read(4))
        frames = tuple(parse_frame(stream) for _ in range(frame_count))
        return Action(frames)

    return tuple(parse_action() for _ in range(count))


def parse_events(stream):

    count, = struct.unpack('<i', stream.read(4))

    # parse each 40 character event name as a string.
    def parse_event_name():
        name = stream.read(40)
        end = 40
        with contextlib.suppress(ValueError):
            end = name.index(0)
        return name[:end].decode()

    return tuple(parse_event_name() for _ in range(count))


def parse_delays(stream):
    for action in stream.actions:
        action.delay, = struct.unpack('<f', stream.read(4))


class ACT(io.BytesIO):

    def __init__(self, stream):
        stream.seek(0)
        super().__init__(stream.read())

        self.version = get_version(self, b'AC', supported=SUPPORTED_VERSIONS)

        self.actions = parse_actions(self)

        self.events = tuple()
        if self.version >= 0x201:
            self.events = parse_events(self)

        if self.version >= 0x202:
            parse_delays(self)
