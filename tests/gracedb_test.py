import unittest
import os
import shutil

from bilby_pipe import gracedb, main
from bilby_pipe.utils import BilbyPipeError

import numpy as np

CERT_ALIAS = "X509_USER_PROXY"


class TestGraceDB(unittest.TestCase):
    def setUp(self):
        self.directory = os.path.abspath(os.path.dirname(__file__))
        self.outdir = "outdir"
        self.example_gracedb_uid = "G298936"
        self.example_gracedb_uid_outdir = "outdir_{}".format(self.example_gracedb_uid)
        self.cert_dummy_path = os.path.join(self.directory, "temp/certdir/")
        os.makedirs(self.cert_dummy_path)
        os.makedirs(self.outdir)

    def tearDown(self):
        if os.path.isdir(self.outdir):
            shutil.rmtree(self.outdir)
        if os.path.isdir(self.example_gracedb_uid_outdir):
            shutil.rmtree(self.example_gracedb_uid_outdir)
        if os.path.isdir(self.cert_dummy_path):
            shutil.rmtree(self.cert_dummy_path)

    def test_x509userproxy(self):
        """
        Tests if bilby_pipe.gracedb.x509userproxy(outdir)
        can move the user's CERT_ALIAS from the CERT_ALIAS dir to the outdir
        """
        # make temp cert file
        cert_alias_path = os.path.join(self.cert_dummy_path, CERT_ALIAS)
        temp_cert = open(cert_alias_path, "w")
        temp_cert.write("this is a test")
        temp_cert.close()

        # set os environ cert path
        os.environ[CERT_ALIAS] = cert_alias_path

        # get new cert path
        out = gracedb.x509userproxy(outdir=self.outdir)
        new_cert_path = os.path.join(self.outdir, "." + CERT_ALIAS)

        self.assertEqual(out, new_cert_path)

    def test_x509userproxy_no_cert(self):
        """
        No X509_USER_PROXY present, so gracedb.x509userprox is None
        """
        out = gracedb.x509userproxy(outdir=self.outdir)
        self.assertEqual(out, None)

    def test_x509userproxy_no_file(self):
        # set os environ cert path to path without cert
        os.environ.update({CERT_ALIAS: ""})

        out = gracedb.x509userproxy(outdir=self.outdir)
        self.assertEqual(out, None)

    # def test_read_from_gracedb(self):
    #    uid = "G298936"
    #    gracedb_url = 'https://gracedb.ligo.org/api/'
    #    gracedb.read_from_gracedb(uid, gracedb_url, self.outdir)

    def test_read_from_json(self):
        example_json_data = "examples/G298936.json"
        out = gracedb.read_from_json(example_json_data)
        self.assertIsInstance(out, dict)

    def test_read_from_json_not_a_file(self):
        with self.assertRaises(FileNotFoundError):
            gracedb.read_from_json("not-a-file")

    def test_create_config_file(self):
        example_json_data = "examples/{}.json".format(self.example_gracedb_uid)
        candidate = gracedb.read_from_json(example_json_data)
        # Create ini file
        filename = gracedb.create_config_file(
            candidate, self.example_gracedb_uid, self.outdir
        )
        # Check it exists
        self.assertTrue(os.path.isfile(filename))
        # Read in using bilby_pipe
        parser = main.create_parser(top_level=True)
        args = parser.parse_args([filename])
        # Check it is set up correctly
        self.assertEqual(args.label, self.example_gracedb_uid)
        self.assertEqual(args.prior_file, "4s")

    def test_create_config_file_roq(self):
        gracedb_uid = "G298936"
        example_json_data = "examples/{}.json".format(gracedb_uid)
        candidate = gracedb.read_from_json(example_json_data)
        candidate["extra_attributes"]["CoincInspiral"]["mchirp"] = 2.1
        # Create ini file
        filename = gracedb.create_config_file(candidate, gracedb_uid, self.outdir)
        # Check it exists
        self.assertTrue(os.path.isfile(filename))
        # Read in using bilby_pipe
        parser = main.create_parser(top_level=True)
        args = parser.parse_args([filename])
        # Check it is set up correctly
        self.assertEqual(args.label, gracedb_uid)
        self.assertEqual(args.prior_file, "128s")
        self.assertEqual(args.likelihood_type, "ROQGravitationalWaveTransient")
        self.assertEqual(args.roq_folder, "/home/cbc/ROQ_data/IMRPhenomPv2/128s")

    def test_create_config_file_no_chirp_mass(self):
        gracedb_uid = "G298936"
        example_json_data = "examples/{}.json".format(gracedb_uid)
        candidate = gracedb.read_from_json(example_json_data)
        del candidate["extra_attributes"]["CoincInspiral"]["mchirp"]
        with self.assertRaises(BilbyPipeError):
            gracedb.create_config_file(candidate, gracedb_uid, self.outdir)

    def test_determine_prior_file_from_parameters(self):
        from bilby_pipe.input import Input

        # simple check that a prior is returned for the input range
        for chirp_mass in np.linspace(0.1, 100, 100):
            prior = gracedb.determine_prior_file_from_parameters(chirp_mass)
            self.assertTrue(prior in Input.get_default_prior_files())

    def test_parse_args(self):
        example_json_data = "examples/{}.json".format(self.example_gracedb_uid)
        parser = gracedb.create_parser()
        args = parser.parse_args(["--json", example_json_data])
        self.assertEqual(args.gracedb, None)
        self.assertEqual(args.json, example_json_data)
        self.assertEqual(args.local, False)
        self.assertEqual(args.submit, False)
        self.assertEqual(args.outdir, None)
        self.assertEqual(args.gracedb_url, "https://gracedb.ligo.org/api/")

    # Testing failing due to pesummary
    # def test_main(self):
    #     gracedb_uid = "G298936"
    #     example_json_data = "examples/{}.json".format(gracedb_uid)
    #     parser = gracedb.create_parser()
    #     args = parser.parse_args(["--json", example_json_data])
    #     gracedb.main(args)
    #     files = glob.glob(self.example_gracedb_uid_outdir + "/submit/*")
    #     # Check this creates jobs
    #     self.assertEqual(len(files), 9)


if __name__ == "__main__":
    unittest.main()
