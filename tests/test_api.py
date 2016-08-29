import pytest
import pygrf


def test_entry_points():
    pygrf.open
    pygrf.open_grf


class TestOpen:

    @pytest.mark.parametrize('filename, subcommand', (
        ('test.grf', 'pygrf.api.open_grf'),
    ))
    def test_call_subcommand(self, mocker, filename, subcommand):
        opener = mocker.patch(subcommand)
        assert pygrf.open(filename) == opener.return_value
        opener.assert_called_once_with(filename)

    def test_raise_value_error_invalid_filetype(self):
        with pytest.raises(ValueError):
            pygrf.open('something.abc')
