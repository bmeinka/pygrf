import filecmp
import io
import os
import pytest

from pygrf import open_grf
from pygrf import InvalidGRFError
from pygrf.grf import GRF


@pytest.mark.parametrize('name, expected', (('a.grf', 1), ('ab.grf', 2)))
def test_grf_has_correct_length(data_files, name, expected):
    grf = open_grf(data_files[name])
    length = len(grf)
    assert length == expected


@pytest.mark.parametrize('name, expected', (('a.grf', 0x200), ('ab.grf', 0x200)))
def test_grf_has_correct_version(data_files, name, expected):
    grf = open_grf(data_files[name])
    assert grf.version == expected


@pytest.mark.parametrize('name, expected', (('a.grf', True), ('ab.grf', False)))
def test_grf_has_correct_encryption(data_files, name, expected):
    grf = open_grf(data_files[name])
    assert grf.allow_encryption == expected


@pytest.mark.parametrize('name', (
    'invalid_signature.grf', 'invalid_encryption.grf', 'invalid_version.grf',
    'invalid_filecount.grf'
))
def test_grf_raises_invalid_grf_error(data_files, name):
    with pytest.raises(InvalidGRFError):
        open_grf(data_files[name])


def test_grf_close_closes_source(data_files):
    source = open(data_files['ab.grf'], 'rb')
    grf = GRF(source)
    grf.close()
    assert source.closed


def test_grf_context_exit_closes_source(data_files):
    source = open(data_files['ab.grf'], 'rb')
    with GRF(source):
        pass
    assert source.closed


@pytest.mark.parametrize('name, expected', (('a.grf', 1), ('ab.grf', 2)))
def test_grf_files_has_correct_length(data_files, name, expected):
    grf = open_grf(data_files[name])
    files_length = len(list(grf.files()))
    assert files_length == expected


@pytest.mark.parametrize('name, expected', (
    ('a.grf', {'a.txt'}),
    ('ab.grf', {'a.txt', 'b.dat'})
))
def test_grf_files_has_correct_files(data_files, name, expected):
    grf = open_grf(data_files[name])
    names = set(grf.files())
    assert names == expected


@pytest.mark.parametrize('name, expected', (('a.grf', 1), ('ab.grf', 2)))
def test_grf_iterator_has_correct_length(data_files, name, expected):
    grf = open_grf(data_files[name])
    iterator_length = len(list(grf))
    assert iterator_length == expected


@pytest.mark.parametrize('name, expected', (
    ('a.grf', {'a.txt'}),
    ('ab.grf', {'a.txt', 'b.dat'})
))
def test_grf_iterator_has_correct_files(data_files, name, expected):
    grf = open_grf(data_files[name])
    names = {f.filename for f in grf}
    assert names == expected


@pytest.mark.parametrize('name', ('a.grf', 'ab.grf'))
def test_grf_iterates_twice(data_files, name):
    grf = open_grf(data_files[name])
    first = {f.filename for f in grf}
    second = {f.filename for f in grf}
    assert first == second


def test_grf_iterator_contains_opened_files(data_files):
    grf = open_grf(data_files['ab.grf'])
    for f in grf:
        assert f == grf.open(f.filename)


def test_grf_decodes_filenames(data_files):
    expected = {line.strip() for line in open(data_files['encoding.txt'])}
    grf = open_grf(data_files['encoding.grf'])
    names = {f.filename for f in grf}
    assert names == expected


@pytest.mark.parametrize('name', ('a.txt', 'b.dat'))
def test_grf_open_file_has_correct_filename(data_files, name):
    grf = open_grf(data_files['ab.grf'])
    opened_file = grf.open(name)
    assert opened_file.filename == name


@pytest.mark.parametrize('name', ('a.txt', 'b.dat'))
def test_grf_open_file_has_correct_data(data_files, name):
    expected = open(data_files[name], 'rb').read()
    grf = open_grf(data_files['ab.grf'])
    opened_file = grf.open(name)
    assert opened_file.data == expected


def test_grf_open_file_is_io_object(data_files):
    grf = open_grf(data_files['ab.grf'])
    opened_file = grf.open('b.dat')
    assert isinstance(opened_file, io.IOBase)


def test_grf_open_empty_file(data_files):
    expected = b''
    # encoding.grf contains only empty files
    grf = open_grf(data_files['encoding.grf'])
    name = list(grf.files()).pop()
    opened_file = grf.open(name)
    assert opened_file.data == expected


def tset_grf_open_raises_file_not_found_error(data_files):
    grf = open_grf(data_files['ab.grf'])
    with pytest.raises(FileNotFoundError):
        grf.open('invalid file name')


@pytest.mark.parametrize('name', ('a.txt', 'b.dat'))
def test_grf_extract_creates_correct_file(tmpdir, data_files, name):
    expected_path = os.path.join(tmpdir.strpath, 'data', name)
    grf = open_grf(data_files['ab.grf'])
    grf.extract(name, tmpdir.strpath)
    assert os.path.exists(expected_path)


@pytest.mark.parametrize('name', ('a.txt', 'b.dat'))
def test_grf_extract_created_file_has_correct_data(tmpdir, data_files, name):
    original_path = data_files[name]
    expected_path = os.path.join(tmpdir.strpath, 'data', name)
    grf = open_grf(data_files['ab.grf'])
    grf.extract(name, tmpdir.strpath)
    assert filecmp.cmp(original_path, expected_path, False)


def test_grf_extract_raises_file_not_found_error(data_files):
    grf = open_grf(data_files['ab.grf'])
    with pytest.raises(FileNotFoundError):
        grf.extract('invalid file name')
