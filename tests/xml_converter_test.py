import os
import subprocess
import unittest

import bilby_pipe.xml_converter


class TestInput(unittest.TestCase):
    def setUp(self):
        self.test_xml_file = "tests/lalinference_test_injection_standard.xml"

    def tearDown(self):
        pass

    def test_default_file_conversion(self):
        subprocess.call(
            [
                " ".join(
                    [
                        "bilby_pipe_xml_converter",
                        self.test_xml_file,
                        "--reference-frequency 20",
                    ]
                )
            ],
            shell=True,
        )
        self.assertTrue(os.path.isfile(self.test_xml_file.replace("xml", "json")))

    def test_json_file_conversion(self):
        subprocess.call(
            [
                " ".join(
                    [
                        "bilby_pipe_xml_converter",
                        self.test_xml_file,
                        "--reference-frequency 20",
                        "--format json",
                    ]
                )
            ],
            shell=True,
        )
        self.assertTrue(os.path.isfile(self.test_xml_file.replace("xml", "json")))

    def test_dat_file_conversion(self):
        subprocess.call(
            [
                " ".join(
                    [
                        "bilby_pipe_xml_converter",
                        self.test_xml_file,
                        "--reference-frequency 20",
                        "--format dat",
                    ]
                )
            ],
            shell=True,
        )
        self.assertTrue(os.path.isfile(self.test_xml_file.replace("xml", "dat")))

    def test_conversion(self):
        df = bilby_pipe.xml_converter.xml_to_dataframe(self.test_xml_file, 20)
        row = df.iloc[0]
        self.assertEqual(row.mass_1, 30)
        self.assertEqual(row.a_1, 0)
        self.assertEqual(row.a_2, 0)
        self.assertEqual(row.tilt_1, 1.5707963267948966)


if __name__ == "__main__":
    unittest.main()
