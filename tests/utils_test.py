import os
import unittest
import bilby_pipe
import shutil
import logging
import sys


class TestUtils(unittest.TestCase):

    def setUp(self):
        self.outdir = 'outdir'
        if not os.path.exists(self.outdir):
            os.makedirs(self.outdir)

    def tearDown(self):
        logger = logging.getLogger('bilby_pipe')
        for handler in logger.handlers[:]:
            logger.removeHandler(handler)
        shutil.rmtree(self.outdir, ignore_errors=True)

    def test_directory_creation(self):
        directory = self.outdir + '/test-dir'
        self.assertFalse(os.path.isdir(directory))
        bilby_pipe.utils.check_directory_exists_and_if_not_mkdir(directory)
        self.assertTrue(os.path.isdir(directory))

    def test_set_log_level(self):
        bilby_pipe.utils.setup_logger(log_level='info')
        logger = logging.getLogger('bilby_pipe')
        self.assertEqual(logger.level, logging.INFO)

    def test_set_verbose(self):
        sys.argv.append('-v')
        bilby_pipe.utils.setup_logger(log_level='info')
        logger = logging.getLogger('bilby_pipe')
        self.assertEqual(logger.level, logging.DEBUG)
        sys.argv.pop(-1)

    def test_unknown_log_level(self):
        with self.assertRaises(ValueError):
            bilby_pipe.utils.setup_logger(log_level='NOTANERROR')

    def test_write_to_file(self):
        bilby_pipe.utils.setup_logger(outdir=self.outdir, label='TEST')
        self.assertTrue(os.path.isfile('{}/{}.log'.format(self.outdir, "TEST")))


if __name__ == '__main__':
    unittest.main()
