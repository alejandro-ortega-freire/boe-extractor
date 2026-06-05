import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

from docx import Document

from source.anexo_v_writer import build_anexo_v_filename, create_anexo_v_docx
from source.models import BasicData, TrainingModule, TrainingUnit


class AnexoVWriterTests(unittest.TestCase):
    def test_anexo_v_uses_evaluation_planning_header_texts(self):
        with TemporaryDirectory() as tmp:
            output_path = Path(tmp) / "anexoV.docx"
            create_anexo_v_docx(
                BasicData(
                    codigo="TEST0101",
                    nombre="Certificado de prueba.",
                    familia="Familia de prueba.",
                    nivel="2.",
                ),
                TrainingModule(
                    identifier="MF0001_1: Módulo de prueba",
                    hours="100",
                    objective="Objetivo de prueba.",
                ),
                "100 horas",
                output_path,
                schedule={},
                add_header_footer=lambda doc, teacher_name: None,
                teacher_name="Docente",
            )

            text = "\n".join(paragraph.text for paragraph in Document(output_path).paragraphs)

        self.assertIn("ANEXO V - MF0001_1 Módulo de prueba", text)
        self.assertIn("Planificación de la evaluación del aprendizaje", text)
        self.assertIn("PLANIFICACIÓN DE LA EVALUACIÓN DEL APRENDIZAJE", text)
        self.assertIn("1 Identificar las actividades e instrumentos de evaluación", text)
        self.assertIn("2 Las fechas de evaluación estarán actualizadas", text)
        self.assertNotIn("ANEXO IV", text)
        self.assertNotIn("PROGRAMACIÓN DIDÁCTICA DEL MÓDULO PROFESIONAL", text)

    def test_anexo_v_filename_matches_module_and_certificate(self):
        self.assertEqual(
            build_anexo_v_filename("MF0001_1", "TEST0101"),
            "anexoV_MF0001_1_TEST0101.docx",
        )

    def test_anexo_v_table_adds_one_row_per_uf(self):
        with TemporaryDirectory() as tmp:
            output_path = Path(tmp) / "anexoV.docx"
            create_anexo_v_docx(
                BasicData(codigo="TEST0101"),
                TrainingModule(
                    identifier="MF0001_1: Módulo de prueba",
                    ufs=[
                        TrainingUnit(code="UF0001", name="Primera unidad"),
                        TrainingUnit(code="UF0002", name="Segunda unidad"),
                    ],
                ),
                "100 horas",
                output_path,
                schedule={},
                add_header_footer=lambda doc, teacher_name: None,
            )

            table = Document(output_path).tables[0]

        self.assertEqual(len(table.rows), 4)
        self.assertEqual(table.rows[0].cells[0].text, "MÓDULO\nPROFESIONAL")
        self.assertEqual(table.rows[1].cells[0].text, "BLOQUES\nFORMATIVOS")
        self.assertEqual(table.rows[0].cells[1].text, "DURANTE EL PROCESO DE\nAPRENDIZAJE")
        self.assertEqual(table.rows[1].cells[1].text, "ACTIVIDADES E INSTRUMENTOS\nDE EVALUACIÓN¹")
        self.assertEqual(table.rows[0].cells[2].text, "Realización de la evaluación")
        self.assertEqual(table.rows[1].cells[2].text, "Espacios")
        self.assertEqual(table.rows[1].cells[3].text, "Duración")
        self.assertEqual(table.rows[1].cells[4].text, "Fechas de\nevaluación²")
        self.assertEqual(table.rows[2].cells[0].text, "UF0001: Primera unidad")
        self.assertEqual(table.rows[3].cells[0].text, "UF0002: Segunda unidad")

    def test_anexo_v_table_uses_module_name_when_module_has_no_ufs(self):
        with TemporaryDirectory() as tmp:
            output_path = Path(tmp) / "anexoV.docx"
            create_anexo_v_docx(
                BasicData(codigo="TEST0101"),
                TrainingModule(identifier="MF0001_1: Módulo de prueba"),
                "100 horas",
                output_path,
                schedule={},
                add_header_footer=lambda doc, teacher_name: None,
            )

            table = Document(output_path).tables[0]

        self.assertEqual(len(table.rows), 3)
        self.assertEqual(table.rows[2].cells[0].text, "MF0001_1: Módulo de prueba")


if __name__ == "__main__":
    unittest.main()
