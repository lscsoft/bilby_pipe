import unittest
import os
import shutil
from bilby_pipe import gracedb

CERT_ALIAS = "X509_USER_PROXY"


class TestGraceDB(unittest.TestCase):
    def setUp(self):
        self.directory = os.path.abspath(os.path.dirname(__file__))
        self.outdir = "outdir"
        self.cert_dummy_path = os.path.join(self.directory, "temp/certdir/")
        os.makedirs(self.cert_dummy_path)
        os.makedirs(self.outdir)

    def tearDown(self):
        if os.path.isdir(self.outdir):
            shutil.rmtree(self.outdir)
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


if __name__ == "__main__":
    unittest.main()
