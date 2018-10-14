import unittest

import bilby_pipe


class TestSummaryGenerator(unittest.TestCase):

    def setUp(self):
        self.header = bilby_pipe.summary.header
        self.section_template = bilby_pipe.summary.section_template
        self.footer = bilby_pipe.summary.footer

    def tearDown(self):
        del self.header
        del self.section_template
        del self.footer

    def test_get_section(self):
        params = dict(title='test', corner_file_path='test')
        self.assertEqual(self.section_template.format(**params),
                         bilby_pipe.summary.get_section(**params))


if __name__ == '__main__':
    unittest.main()
