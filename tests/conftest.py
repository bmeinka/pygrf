import os
import shutil
import pytest


@pytest.fixture
def data_files(request, tmpdir):

    class DataFile:

        def __init__(self):
            self.data_dir, _ = os.path.splitext(request.module.__file__)
            self.tmp_dir = tmpdir.strpath
            assert os.path.isdir(self.data_dir)

        def get_file(self, filename):
            source_path = os.path.join(self.data_dir, filename)
            if not os.path.exists(source_path):
                raise FileNotFoundError()
            temp_path = os.path.join(self.tmp_dir, filename)
            shutil.copyfile(source_path, temp_path)
            return temp_path

        def __getitem__(self, filename):
            return self.get_file(filename)

    return DataFile()
