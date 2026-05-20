import unittest

from source.training_section import is_module_header, is_practice_module_header

from tests.helpers import MAMD0309_PDF, find_training_module, payload_for, require_pdf


class TrainingSectionTests(unittest.TestCase):
    def test_detects_module_header_with_and_without_accent(self):
        self.assertTrue(is_module_header("MÓDULO FORMATIVO 1"))
        self.assertTrue(is_module_header("MODULO FORMATIVO 2"))

    def test_detects_practice_module_header_with_and_without_accent(self):
        self.assertTrue(is_practice_module_header("MÓDULO DE PRÁCTICAS PROFESIONALES"))
        self.assertTrue(is_practice_module_header("MODULO DE PRÁCTICAS PROFESIONALES"))

    def test_mamd0309_keeps_ufs_in_their_correct_modules(self):
        require_pdf(self, MAMD0309_PDF)
        payload = payload_for("MAMD0309.pdf")

        mf0174 = find_training_module(payload, "MF0174_3")
        mf0175 = find_training_module(payload, "MF0175_3")

        self.assertEqual([uf.code for uf in mf0174.ufs], ["UF1182", "UF1183", "UF1184"])
        self.assertEqual([uf.code for uf in mf0175.ufs], ["UF1185", "UF1186", "UF1187"])


if __name__ == "__main__":
    unittest.main()
