import unittest

from source.anexo_iii_writer import title_without_hours
from source.anexo_iv_writer import module_identifier_without_hours, module_title
from source.models import TrainingModule
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

    def test_module_titles_used_in_annexes_do_not_keep_trailing_hours(self):
        module_text = (
            "MF0615_3: Proyectos de montaje de instalaciones de energía eólica. "
            "(120 horas)."
        )
        module = TrainingModule(identifier=module_text, hours="120")

        self.assertEqual(
            title_without_hours(module_text),
            "MF0615_3: Proyectos de montaje de instalaciones de energía eólica."
        )
        self.assertEqual(
            module_identifier_without_hours(module),
            "MF0615_3: Proyectos de montaje de instalaciones de energía eólica."
        )
        self.assertEqual(
            module_title(module),
            "MF0615_3 Proyectos de montaje de instalaciones de energía eólica."
        )


if __name__ == "__main__":
    unittest.main()
