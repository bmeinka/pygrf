import contextlib
import io
import struct
from collections import namedtuple
from typing import NamedTuple, Tuple
#from .exceptions import FileParseError 
from .util import get_version
from .graphics import Point, Color, Vector2


class Layer(NamedTuple):
    offset: Point
    index: int
    flipped: bool
    color: Color = Color(255, 255, 255, 255)
    zoom: Vector2 = Vector2(1.0, 1.0)
    angle: float = 0.0


class Frame(NamedTuple):
    layers: Tuple[Layer]
    trigger: int = -1


class Animation(NamedTuple):
    frames: Tuple[Frame]
    interval: float = 4.0


def parse_layer(stream):
    """ Parse a layer of a frame of an animation in an ACT file.

    :param stream: the act file to parse from

    Each layer consists of the following information:

    ======  ====  ======  =======  ============================
    field   size  type    version  purpose
    ======  ====  ======  =======  ============================
    offset  8     int32   0x100    offset from center of frame
    index   4     uint32  0x100    image index in spr file
    flags   4     uint32  0x100    image is flipped if non-zero
    color   4     byte    0x200    ABGR? color for tinting
    zoom    4     float   0x200    image scale
    zoom y  4     float   0x204    image scale for y axis
    angle   4     float   0x200    rotation of the image
    unused  4     int32   0x200
    unused  8     int32   0x205
    ======  ====  ======  =======  ============================
    """ 
    x, y, index, flags = struct.unpack('<iiII', stream.read(16))
    offset = Point(x, y)
    layer = Layer(offset, index, flags != 0)

    if stream.version >= 0x200:
        color = Color(*struct.unpack('<4B', stream.read(4)))
        layer = layer._replace(color=color)

    if stream.version >= 0x204:
        zoom = Vector2(*struct.unpack('<ff', stream.read(8)))
        layer = layer._replace(zoom=zoom)
    elif stream.version >= 0x200:
        zoom, = struct.unpack('<f', stream.read(4))
        layer = layer._replace(zoom=Vector2(zoom, zoom))

    if stream.version >= 0x200:
        angle, = struct.unpack('<f', stream.read(4))
        layer = layer._replace(angle=angle)

    if stream.version >= 0x205:
        stream.read(12)
    elif stream.version >= 0x200:
        stream.read(4)

    return layer


def parse_frame(stream):
    """ Parse a frame from an ACT file.

    :param stream: the act file to parse from

    A frame is structured as follows:

    =============  =====  =======  ===================================
    field          type   version  type   purpose
    =============  =====  =======  ===================================
    unused                         32 bytes of "range rects"
    layer count    int32  0x100    the number of layers in the frame
    layers         list   0x100    the layers of the frame
    trigger        int32  0x200    a trigger id, or -1 for none
    anchor count   int32  0x203    the number of anchors for the frame
    anchors        list   0x203    the anchors for the frame
    =============  =====  =======  ===================================
    """
    layer_count, = struct.unpack('<32xi', stream.read(36))
    layers = tuple(parse_layer(stream) for _ in range(layer_count))
    if stream.version >= 0x200:
        trigger, = struct.unpack('<i', stream.read(4))
    else:
        trigger = -1
    # don't know how to use anchor data, so skip it
    if stream.version >= 0x203:
        count, = struct.unpack('<i', stream.read(4))
        stream.read(16 * count)
    return Frame(layers, trigger)


def parse_animation(stream):
    """ Parse an animation from an ACT file.

    :param stream: the act file to parse from

    An animation is made up of a single int32 containing the number of frames
    followed by a list of frames. An animation starts with a default interval
    of 4.0, which will be modified later by the list of animation intervals
    at the end of the act file.
    """
    frame_count, = struct.unpack('<i', stream.read(4))
    frames = (parse_frame(stream) for _ in range(frame_count))
    return Animation(tuple(frames), 4.0)

def parse_triggers(stream):
    """ Parse the triggers defined in an act file.

    :param stream: the act file to parse from

    The triggers are stored in a list in the act file after the animations.
    It starts with an int32 holding the trigger count. After that is a list
    of trigger strings. Each string is held in a 40-byte buffer and
    null-terminated.
    """
    count, = struct.unpack('<i', stream.read(4))
    return tuple(stream.read(40).strip(b'\x00').decode() for _ in range(count))


def parse_intervals(stream):
    """ Parse animation intervals for a stream

    :param stream: the act file to read from

    The animation delays are stored at the end of the file in a simple list.
    """
    intervals = struct.iter_unpack('<f', stream.read())
    stream.animations = tuple(
        animation._replace(interval=interval[0])
        for animation, interval in zip(stream.animations, intervals)
    )


class ACT(io.BytesIO):

    def __init__(self, stream):
        """ Parse an ACT file.

        :param stream: the source binary stream

        An act file begins with a simple header arranged in the following
        manner:

        =========  ====  ======  ====================
        field      size  type    purpose
        =========  ====  ======  ====================
        signature  2     char    verify the file type
        version    2     uint16  the version number
        count      2     uint16  number of animations
        unused     10
        =========  ====  ======  ====================

        After the header, the rest of the file contains the following
        information in this order:

        - list of animations
        - list of sound files/events
        - list of intervals for each animation
        """
        stream.seek(0)
        super().__init__(stream.read())

        self.version = get_version(self, b'AC')
        count, = struct.unpack('<H10x', self.read(12))
        self.animations = tuple(parse_animation(self) for _ in range(count))
        self.triggers = parse_triggers(self)
        parse_intervals(self)