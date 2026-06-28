import unittest

from source.anexo_iii_writer import title_without_hours
from source.anexo_iv_writer import module_identifier_without_hours, module_title
from source.models import TrainingModule
from source.training_section import (
    apply_module_code_corrections,
    extract_training_modules,
    is_module_header,
    is_practice_module_header,
    module_code_corrections,
)

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

    def test_matches_transversal_module_when_detail_code_differs_from_summary(self):
        text = """
        III. FORMACIÓN DEL CERTIFICADO DE PROFESIONALIDAD
        MÓDULO FORMATIVO 2
        Denominación: GESTIÓN DE LA FUERZA DE VENTAS Y EQUIPOS DE COMERCIALES.
        Código: MF0263_3
        Asociado a la Unidad de Competencia:
        UC1001_3: Gestionar la fuerza de ventas y coordinar el equipo de comerciales.
        Duración: 90 horas
        Capacidades y criterios de evaluación
        C1: Calcular y definir la fuerza de ventas.
        Contenidos
        1. Organización del equipo comercial.
        IV. PRESCRIPCIONES DE LOS FORMADORES
        """
        modules = [
            {
                "text": "MF1001_3: (Transversal) Gestión de la fuerza de ventas y equipos de comerciales. (90 horas)",
                "ufs": [],
            }
        ]

        [module] = extract_training_modules(text, modules)

        self.assertEqual(module["identifier"], "MF0263_3: (Transversal) Gestión de la fuerza de ventas y equipos de comerciales.")
        self.assertEqual(module["source_code"], "MF0263_3")
        self.assertEqual(module["summary_code"], "MF1001_3")
        self.assertEqual(module["objective"], "Gestionar la fuerza de ventas y coordinar el equipo de comerciales.")
        self.assertEqual(module["criteria"][0]["text"], "C1: Calcular y definir la fuerza de ventas.")

        corrected_modules = apply_module_code_corrections(modules, module_code_corrections([module]))
        self.assertEqual(
            corrected_modules[0]["text"],
            "MF0263_3: (Transversal) Gestión de la fuerza de ventas y equipos de comerciales. (90 horas)"
        )

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
