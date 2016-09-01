import pytest
from pygrf import open_grf


class TestGRFHeader:

    @pytest.mark.parametrize('filename', (
        'invalid_watermark.grf', 'invalid_encryption.grf',
        'invalid_version.grf', 'invalid_filecount.grf'
    ))
    def test_raise_value_error_bad_header(self, data_files, filename):
        with pytest.raises(ValueError):
            open_grf(data_files[filename])

    @pytest.mark.parametrize('filename, expected', (
        ('a.grf', True), ('ab.grf', False)
    ))
    def test_encryption(self, data_files, filename, expected):
        with open_grf(data_files[filename]) as grf_file:
            assert grf_file.header.allow_encryption == expected

    def test_version(self, data_files):
        with open_grf(data_files['a.grf']) as grf_file:
            assert grf_file.header.version == 0x0200

    @pytest.mark.parametrize('filename, count', (
        ('a.grf', 1), ('ab.grf', 2)
    ))
    def test_file_count(self, data_files, filename, count):
        with open_grf(data_files[filename]) as grf_file:
            assert grf_file.header.file_count == count

    @pytest.mark.parametrize('filename, offset', (
        ('a.grf', 62), ('ab.grf', 330)
    ))
    def test_offset(self, data_files, filename, offset):
        with open_grf(data_files[filename]) as grf_file:
            assert grf_file.header.entry_point == offset


class TestGRFFiles:

    @pytest.mark.parametrize('filename, files', (
        ('a.grf', ['data\\a.txt']), ('ab.grf', ['data\\a.txt', 'data\\b.dat'])
    ))
    def test_files_listed(self, data_files, filename, files):
        with open_grf(data_files[filename]) as grf_file:
            for f in files:
                assert f in grf_file.files
            assert len(grf_file.files) == len(files)

    def test_file_has_filename(self, data_files):
        names = ['data\\a.txt', 'data\\b.dat']
        with open_grf(data_files['ab.grf']) as grf_file:
            for name in names:
                f = grf_file.files[name]
                assert f.filename == name

    def test_file_has_stored_size(self, data_files):
        sizes = {'data\\a.txt': 16, 'data\\b.dat': 268}
        with open_grf(data_files['ab.grf']) as grf_file:
            for name, size in sizes.items():
                assert grf_file.files[name].archived_size == size
    
    def test_file_has_compressed_size(self, data_files):
        sizes = {'data\\a.txt': 15, 'data\\b.dat': 267}
        with open_grf(data_files['ab.grf']) as grf_file:
            for name, size in sizes.items():
                assert grf_file.files[name].compressed_size == size

    def test_file_has_real_size(self, data_files):
        sizes = {'data\\a.txt': 7, 'data\\b.dat': 256}
        with open_grf(data_files['ab.grf']) as grf_file:
            for name, size in sizes.items():
                assert grf_file.files[name].real_size == size

    def test_file_has_position(self, data_files):
        positions = {'data\\a.txt': 0, 'data\\b.dat': 16}
        with open_grf(data_files['ab.grf']) as grf_file:
            for name, position in positions.items():
                assert grf_file.files[name].position == position

    def test_file_is_flagged_as_file(self, data_files):
        files = ['data\\a.txt', 'data\\b.dat']
        with open_grf(data_files['ab.grf']) as grf_file:
            for name in files:
                assert grf_file.files[name].is_file == True
                assert grf_file.files[name].is_dir == False
