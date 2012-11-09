import unittest
from path import path
from search import available_files, construct_tree

class RepoTest(unittest.TestCase):

    def test_available_files(self):
        tree = construct_tree(path('/home/mihai/Work/pubdocs/tests/repo'))
        import pdb; pdb.set_trace()
