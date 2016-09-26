import io
import pytest

from pygrf import open_gat
from pygrf import InvalidGATError


@pytest.mark.parametrize('name, expected', (('a.gat', 10), ('b.gat', 100)))
def test_gat_has_correct_width(data_files, name, expected):
    gat = open_gat(data_files[name])
    assert gat.width == expected


@pytest.mark.parametrize('name, expected', (('a.gat', 10), ('b.gat', 50)))
def test_gat_has_correct_height(data_files, name, expected):
    gat = open_gat(data_files[name])
    assert gat.height == expected


@pytest.mark.parametrize('name', ('a.gat', 'b.gat'))
def test_gat_has_correct_size(data_files, name):
    gat = open_gat(data_files[name])
    assert gat.size == (gat.width, gat.height)


@pytest.mark.parametrize('name', (
    'invalid_signature.gat', 'invalid_tile_count.gat', 'invalid_tile.gat'
))
def test_open_gat_raises_gat_error(data_files, name):
    with pytest.raises(InvalidGATError):
        open_gat(data_files[name])


def test_gat_is_io_object(data_files):
    gat = open_gat(data_files['a.gat'])
    assert isinstance(gat, io.IOBase)


@pytest.mark.parametrize('name', ('a.gat', 'b.gat'))
def test_gat_data_matches_source_data(data_files, name):
    source = open(data_files[name], 'rb')
    gat = open_gat(data_files[name])
    assert gat.read() == source.read()


@pytest.mark.parametrize('x, y, expected', ((0, 0, 0), (1, 1, 1), (2, 2, 2)))
def test_gat_tile_has_correct_type(data_files, x, y, expected):
    gat = open_gat(data_files['a.gat'])
    tile = gat[x, y]
    assert tile.type == expected


@pytest.mark.parametrize('x, y, heights', (
    (0, 0, (0.0, 0.0, 0.0, 0.0)), (1, 1, (40.0, 40.0, 40.0, 40.0)),
    (2, 2, (0.0, 10.0, 20.0, 30.0))
))
def test_gat_tile_has_correct_heights(data_files, x, y, heights):
    gat = open_gat(data_files['a.gat'])
    bottom_left, bottom_right, top_left, top_right = heights
    tile = gat[x, y]
    assert tile.bottom_left == bottom_left
    assert tile.bottom_right == bottom_right
    assert tile.top_left == top_left
    assert tile.top_right == top_right


@pytest.mark.parametrize('x, y, altitude', ((0, 0, 0.0), (1, 1, 40.0), (2, 2, 15.0)))
def test_gat_tile_has_correct_altitude(data_files, x, y, altitude):
    gat = open_gat(data_files['a.gat'])
    tile = gat[x, y]
    assert tile.altitude == altitude


@pytest.mark.parametrize('x, y', ((0, 10), (0, -1), (10, 0)))
def test_gat_tile_raise_index_error_bad_coordinates(data_files, x, y):
    gat = open_gat(data_files['a.gat'])
    with pytest.raises(IndexError):
        gat[x, y]
