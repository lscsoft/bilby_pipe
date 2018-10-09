import unittest

import bilby_pipe


class TestDag(unittest.TestCase):

    def setUp(self):
        self.default_args = ['tests/test_ini_file.ini']

    def tearDown(self):
        pass

    def test_ini_fail(self):
        args = ['not_a_file']
        with self.assertRaises(SystemExit):
            bilby_pipe.parse_args(args)

    def test_ini(self):
        args, unknown_args = bilby_pipe.parse_args(self.default_args)
        self.assertEquals(args.ini, self.default_args[0])
        self.assertEquals(args.accounting, 'test.test')
        self.assertEquals(args.executable, 'file.py')

    def test_empty_unknown_args(self):
        args, unknown_args = bilby_pipe.parse_args(self.default_args)
        self.assertEquals(unknown_args, [])

    def test_unknown_args(self):
        expected_unknown_args = ['--other', 'thing']
        args = self.default_args + expected_unknown_args
        args, unknown_args = bilby_pipe.parse_args(args)
        self.assertEquals(unknown_args, expected_unknown_args)


if __name__ == '__main__':
    unittest.main()
