""" types used in computer graphics """
from typing import NamedTuple, Sequence


class Point(NamedTuple):
    """ a 2D integer point """
    x: int
    y: int


class Vector2(NamedTuple):
    """ a 2D vector """
    x: float
    y: float


class Color(NamedTuple):
    """ an RGBA color """
    r: int
    g: int
    b: int
    a: int

    @classmethod
    def from_rgba32(cls, color):
        """ convert an rgba 32-bit integer to a color

        >>> Color.from_rgba32(0)
        Color(r=0, b=0, g=0, a=0)
        >>> Color.from_rgba32(2160853247)
        Color(r=128, g=204, b=0, a=255)
        """
        red = (color & 0xff000000) >> 24
        green = (color & 0xff0000) >> 16
        blue = (color & 0xff00) >> 8
        alpha = color & 0xff
        return cls(red, green, blue, alpha)

    def to_rgba32(self):
        """ convert the color to an rgba 32-bit integer

        >>> Color(128, 204, 0, 255).to_rgba32()
        2160853247
        >>> Color(0, 0, 0, 0).to_rgba32()
        0
        """
        red = self.r << 24
        green = self.g << 16
        blue = self.b << 8
        alpha = self.a
        return red + blue + green + alpha


class Image(NamedTuple):
    """ a 2D image with a width, height and pixel data """
    width: int
    height: int
    pixels: Sequence[Color]
