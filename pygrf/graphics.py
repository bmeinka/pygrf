""" types used in computer graphics """
from typing import NamedTuple


class Point(NamedTuple):
    x: int
    y: int


class Vector2(NamedTuple):
    x: float
    y: float


class Color(NamedTuple):
    r: int
    g: int
    b: int
    a: int