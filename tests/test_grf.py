import os
import json
import pytest
import filecmp
from pygrf import open_grf


class TestHeader:

    def test_header_has_correct_data(self, data_files):
        with open(data_files['grf_info.json']) as info_file:
            file_info = json.load(info_file)

        for name, info in file_info.items():
            with open_grf(data_files[name]) as grf_file:
                header = grf_file.header
            assert header.allow_encryption == info['allow_encryption']
            assert header.index_offset == info['index_offset']
            assert header.file_count == info['file_count']
            assert header.version == info['version']

    @pytest.mark.parametrize('filename', (
        'invalid_signature.grf', 'invalid_encryption.grf',
        'invalid_version.grf', 'invalid_filecount.grf'
    ))
    def test_raise_value_error_bad_header(self, data_files, filename):
        with pytest.raises(ValueError):
            open_grf(data_files[filename])


class TestIndex:

    @pytest.mark.parametrize('filename', ('a.grf', 'ab.grf'))
    def test_index_has_correct_count(self, data_files, filename):
        with open_grf(data_files[filename]) as grf_file:
            assert len(grf_file.index) == grf_file.header.file_count

    @pytest.mark.parametrize('filename, files', (
        ('a.grf', ['a.txt']), ('ab.grf', ['a.txt', 'b.dat'])
    ))
    def test_index_get_file(self, data_files, filename, files):
        with open_grf(data_files[filename]) as grf_file:
            for f in files:
                assert f in grf_file.index

    def test_decode_filenames(self, data_files):
        with open(data_files['encoding.txt']) as f:
            names = [line.strip() for line in f]
        grf = open_grf(data_files['encoding.grf'])
        for name, header in grf.index:
            assert name in names

    def test_index_raise_error_file_not_found(self, data_files):
        grf = open_grf(data_files['ab.grf'])
        with pytest.raises(KeyError):
            grf.index['invalid file name']

    def test_index_can_iterate(self, data_files):
        files = ['a.txt', 'b.dat']
        grf = open_grf(data_files['ab.grf'])
        for name, header in grf.index:
            assert name in files

    @pytest.mark.parametrize('filename, count', (
        ('ab.grf', 2), ('a.grf', 1)
    ))
    def test_index_iterates_all_files(self, data_files, filename, count):
        counter = 0
        grf = open_grf(data_files[filename])
        for name, header in grf.index:
            counter += 1
        assert counter == count

    def test_index_iterates_twice(self, data_files):
        grf = open_grf(data_files['ab.grf'])
        first = {f: h for f, h in grf.index}
        second = {f: h for f, h in grf.index}
        assert first == second


class TestFileHeader:

    def test_header_has_correct_data(self, data_files):
        with open(data_files['file_info.json']) as info_file:
            file_info = json.load(info_file)
        with open_grf(data_files['ab.grf']) as grf_file:
            for name, size_info in file_info.items():
                info = file_info[name]
                f = grf_file.get(name)

        assert f.header.archived_size == info['archived']
        assert f.header.compressed_size == info['compressed']
        assert f.header.real_size == info['real']
        assert f.header.position == info['position']
        assert f.header.flag == info['flag']


class TestFile:

    @pytest.mark.parametrize('filename', ('a.txt', 'b.dat'))
    def test_file_has_filename(self, data_files, filename):
        with open_grf(data_files['ab.grf']) as grf_file:
            f = grf_file.get(filename)
            assert f.filename == filename

    @pytest.mark.parametrize('filename', ('a.txt', 'b.dat'))
    def test_file_has_correct_data(self, data_files, filename):
        with open(data_files[filename], 'rb') as f:
            expected = f.read()
        with open_grf(data_files['ab.grf']) as grf_file:
            f = grf_file.get(filename)
            assert f.data == expected

    def test_empty_file(self, data_files):
        expected = b''
        # encoding.grf contains only empty files
        grf = open_grf(data_files['encoding.grf'])
        filename, _ = next(iter(grf.index))
        f = grf.get(filename)
        assert f.data == expected

    def test_file_extracts(self, data_files, tmpdir):
        expected_path = os.path.join(tmpdir.strpath, 'a.txt')
        with open_grf(data_files['ab.grf']) as grf_file:
            grf_file.extract('a.txt', tmpdir.strpath)
        assert os.path.exists(expected_path)

    @pytest.mark.parametrize('filename', ('a.txt', 'b.dat'))
    def test_file_extracted_correct_data(self, data_files, tmpdir, filename):
        original_path = data_files[filename]
        result_path = os.path.join(tmpdir.strpath, filename)
        with open_grf(data_files['ab.grf']) as grf_file:
            grf_file.extract(filename, tmpdir.strpath)
        assert filecmp.cmp(original_path, result_path, False)
