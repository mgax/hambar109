import unittest
from path import path
from search import available_files

class RepoTest(unittest.TestCase):

    def test_available_files(self):
        result = available_files(path('/home/mihai/Work/pubdocs/tests/repo'))
        import pdb; pdb.set_trace()
