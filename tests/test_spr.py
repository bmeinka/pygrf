import pytest
import struct
from pygrf import FileParseError # TODO: rename to simply ParseError
from pygrf import open_spr


@pytest.mark.parametrize('filename', (
    'empty.spr',
    'invalid_header.spr',
    'invalid_signature.spr',
    'invalid_version.spr',
))
def test_open_spr_fails_invalid_files(data_files, filename):
    with pytest.raises(FileParseError):
        open_spr(data_files[filename])


@pytest.mark.parametrize('filename, version', (
    ('100.spr', 0x100),
    ('101.spr', 0x101),
    ('200.spr', 0x200),
    ('201.spr', 0x201),
))
def test_spr_has_correct_version(data_files, filename, version):
    spr = open_spr(data_files[filename])
    assert spr.version == version


@pytest.mark.parametrize('filename, count', (
    ('100.spr', 1),
    ('101.spr', 2),
    ('200.spr', 3),
    ('201.spr', 4),
))
def test_spr_has_correct_image_count(data_files, filename, count):
    spr = open_spr(data_files[filename])
    assert len(spr) == count


@pytest.mark.parametrize('index', (5, -5, 1.3, 'wrongtype'))
def test_spr_fail_with_bad_index(data_files, index):
    spr = open_spr(data_files['201.spr'])
    with pytest.raises(IndexError):
        spr[index]


def test_spr_allows_negative_index(data_files):
    spr = open_spr(data_files['201.spr'])
    spr[-3]


def test_spr_fail_no_palette(data_files):
    # v 1.0 does not have an embedded palette, so getting images should fail
    spr = open_spr(data_files['100.spr'])
    with pytest.raises(FileParseError):
        spr[0] # attempt to get the first image


@pytest.mark.parametrize('filename, index, w, h', (
    ('101.spr', 0, 2, 2),
    ('101.spr', 1, 6, 6),
    ('200.spr', 0, 2, 2),
    ('200.spr', 1, 6, 6),
    ('200.spr', 2, 2, 2),
    ('201.spr', 0, 2, 2),
    ('201.spr', 1, 6, 6),
    ('201.spr', 2, 2, 2),
    ('201.spr', 3, 6, 6),
))
def test_spr_image_has_correct_dimensions(data_files, filename, index, w, h):
    spr = open_spr(data_files[filename])
    img = spr[index]
    assert img.width == w
    assert img.height == h

# TODO: test for validity in v1.0
# TODO: palette parsing...


@pytest.mark.parametrize('spr, index, img', (
    ('101.spr', 0, 'first.img'),
    ('101.spr', 1, 'second.img'),
    ('200.spr', 0, 'first.img'),
    ('200.spr', 1, 'second.img'),
    ('200.spr', 2, 'first.img'),
    ('201.spr', 0, 'first.img'),
    ('201.spr', 1, 'second.img'),
    ('201.spr', 2, 'first.img'),
    ('201.spr', 3, 'second.img'),
))
def test_spr_image_has_correct_pixels(data_files, spr, index, img):
    spr = open_spr(data_files[spr])
    image = spr[index]
    pixels = [pixel.to_rgba32() for pixel in image.pixels]
    with open(data_files[img], 'rb') as img_file:
        expected = struct.iter_unpack('<I', img_file.read())
        expected = [p[0] for p in expected]
    assert pixels == expected
