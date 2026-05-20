import unittest

from tests.helpers import MAMD0309_PDF, find_training_module, find_uf, payload_for, require_pdf


class MAMD0309RegressionTests(unittest.TestCase):
    def test_mamd0309_certificate_structure_regression(self):
        require_pdf(self, MAMD0309_PDF)
        payload = payload_for("MAMD0309.pdf")

        self.assertEqual(payload.data.codigo, "MAMD0309")
        self.assertEqual(len(payload.training_modules), 3)

        mf0175 = find_training_module(payload, "MF0175_3")
        self.assertEqual([uf.code for uf in mf0175.ufs], ["UF1185", "UF1186", "UF1187"])

        for uf_code in ("UF1185", "UF1186", "UF1187"):
            with self.subTest(uf=uf_code):
                uf = find_uf(mf0175, uf_code)
                self.assertGreater(len(uf.criteria), 0)
                self.assertGreater(len(uf.contents), 0)


if __name__ == "__main__":
    unittest.main()
