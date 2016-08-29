import pytest
from pygrf import open_grf


class TestGRFHeader:

    @pytest.mark.parametrize('filename', (
        'watermark_invalid.grf', 'encryption_invalid_flag.grf',
        'version_invalid.grf', 'filecount_invalid.grf'
    ))
    def test_raise_value_error_bad_header(self, data_files, filename):
        with pytest.raises(ValueError):
            open_grf(data_files[filename])

    @pytest.mark.parametrize('filename, expected', (
        ('encryption_allow.grf', True), ('encryption_deny.grf', False)
    ))
    def test_encryption(self, data_files, filename, expected):
        with open_grf(data_files[filename]) as grf_file:
            assert grf_file.header.allow_encryption == expected

    def test_version(self, data_files):
        with open_grf(data_files['version_2.grf']) as grf_file:
            assert grf_file.header.version == 0x0200

    @pytest.mark.parametrize('filename, count', (
        ('filecount_50.grf', 50), ('filecount_100.grf', 100)
    ))
    def test_file_count(self, data_files, filename, count):
        with open_grf(data_files[filename]) as grf_file:
            assert grf_file.header.file_count == count

    @pytest.mark.parametrize('filename, offset', (
        ('offset_50.grf', 50), ('offset_100.grf', 100)
    ))
    def test_offset(self, data_files, filename, offset):
        with open_grf(data_files[filename]) as grf_file:
            assert grf_file.header.entry_point == offset
