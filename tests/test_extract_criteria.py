import unittest

from source.extract_criteria import is_criterion_start

from tests.helpers import MAMD0309_PDF, find_training_module, find_uf, payload_for, require_pdf


class ExtractCriteriaTests(unittest.TestCase):
    def test_detects_criterion_start_with_or_without_colon(self):
        self.assertTrue(is_criterion_start("C1: Manejar programas informáticos"))
        self.assertTrue(is_criterion_start("C2 Manejar programas informáticos"))
        self.assertFalse(is_criterion_start("CE1.1 Manejar programas informáticos"))

    def test_mamd0309_uf1186_has_criteria(self):
        require_pdf(self, MAMD0309_PDF)
        payload = payload_for("MAMD0309.pdf")
        uf1186 = find_uf(find_training_module(payload, "MF0175_3"), "UF1186")

        self.assertEqual(len(uf1186.criteria), 2)
        self.assertTrue(uf1186.criteria[0].text.startswith("C1:"))
        self.assertTrue(uf1186.criteria[1].text.startswith("C2:"))


if __name__ == "__main__":
    unittest.main()
