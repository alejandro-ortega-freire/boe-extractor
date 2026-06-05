import unittest
from datetime import date
from pathlib import Path
from tempfile import TemporaryDirectory

from docx import Document
from docx.shared import RGBColor

from source.anexo_v_writer import (
    build_anexo_v_filename,
    clean_evaluation_space_name,
    create_anexo_v_docx,
)
from source.models import BasicData, SummaryModule, TrainingModule, TrainingUnit
from source.schedule import calculate_schedule


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

    def test_anexo_v_splits_module_row_into_evaluation_events(self):
        schedule = calculate_schedule(
            [SummaryModule(text="MF0001_1: Módulo de prueba (60 horas)")],
            6,
            date(2026, 6, 1),
            custom_holidays={},
        )

        with TemporaryDirectory() as tmp:
            output_path = Path(tmp) / "anexoV.docx"
            create_anexo_v_docx(
                BasicData(codigo="TEST0101"),
                TrainingModule(
                    identifier="MF0001_1: Módulo de prueba",
                    hours="60",
                ),
                "60 horas",
                output_path,
                schedule=schedule,
                add_header_footer=lambda doc, teacher_name: None,
            )

            table = Document(output_path).tables[0]
            labels = [row.cells[1].text for row in table.rows[2:]]
            durations = [row.cells[3].text for row in table.rows[2:]]
            dates = [row.cells[4].text for row in table.rows[2:]]

        self.assertEqual(
            labels,
            [
                "E1: Actividad Evaluable",
                "E2: Actividad Evaluable",
                "E3: Actividad Evaluable",
                "Prueba final",
                "Prueba de recuperación",
            ],
        )
        self.assertEqual(durations, ["4 horas", "4 horas", "4 horas", "6 horas", "6 horas"])
        self.assertIn("(Sesión 9)", dates[-2])
        self.assertIn("(Sesión 10)", dates[-1])

    def test_anexo_v_session_numbers_restart_for_each_module(self):
        schedule = calculate_schedule(
            [
                SummaryModule(text="MF0001_1: Primer módulo (30 horas)"),
                SummaryModule(text="MF0002_1: Segundo módulo (30 horas)"),
            ],
            6,
            date(2026, 6, 1),
            custom_holidays={},
        )

        with TemporaryDirectory() as tmp:
            output_path = Path(tmp) / "anexoV.docx"
            create_anexo_v_docx(
                BasicData(codigo="TEST0101"),
                TrainingModule(
                    identifier="MF0002_1: Segundo módulo",
                    hours="30",
                ),
                "60 horas",
                output_path,
                schedule=schedule,
                add_header_footer=lambda doc, teacher_name: None,
            )

            table = Document(output_path).tables[0]
            dates = [row.cells[4].text for row in table.rows[2:]]

        self.assertIn("(Sesión 4)", dates[-2])
        self.assertIn("(Sesión 5)", dates[-1])
        self.assertNotIn("(Sesión 9)", dates[-2])
        self.assertNotIn("(Sesión 10)", dates[-1])

    def test_anexo_v_uses_clean_red_training_spaces(self):
        schedule = calculate_schedule(
            [SummaryModule(text="MF0001_1: Módulo de prueba (30 horas)")],
            6,
            date(2026, 6, 1),
            custom_holidays={},
        )

        with TemporaryDirectory() as tmp:
            output_path = Path(tmp) / "anexoV.docx"
            create_anexo_v_docx(
                BasicData(codigo="TEST0101"),
                TrainingModule(
                    identifier="MF0001_1: Módulo de prueba",
                    hours="30",
                ),
                "30 horas",
                output_path,
                schedule=schedule,
                spaces=[
                    "Aula de gestión de 45 m2 (para 15 alumnos) o de 60 m2 (para 25 alumnos)",
                    "Taller de prácticas de 30 m2 (para 15 alumnos) o de 50 m2 (para 25 alumnos)",
                ],
                add_header_footer=lambda doc, teacher_name: None,
            )

            cell = Document(output_path).tables[0].rows[2].cells[2]
            runs = [
                run
                for paragraph in cell.paragraphs
                for run in paragraph.runs
            ]

        self.assertEqual(cell.text, "Aula de gestión\n\nTaller de prácticas")
        self.assertTrue(runs)
        self.assertTrue(all(run.font.color.rgb == RGBColor(192, 0, 0) for run in runs))

    def test_anexo_v_marks_only_activity_durations_in_red(self):
        schedule = calculate_schedule(
            [SummaryModule(text="MF0001_1: Módulo de prueba (60 horas)")],
            6,
            date(2026, 6, 1),
            custom_holidays={},
        )

        with TemporaryDirectory() as tmp:
            output_path = Path(tmp) / "anexoV.docx"
            create_anexo_v_docx(
                BasicData(codigo="TEST0101"),
                TrainingModule(
                    identifier="MF0001_1: Módulo de prueba",
                    hours="60",
                ),
                "60 horas",
                output_path,
                schedule=schedule,
                add_header_footer=lambda doc, teacher_name: None,
            )

            table = Document(output_path).tables[0]
            activity_duration = table.rows[2].cells[3].paragraphs[0].runs[0]
            final_duration = table.rows[-2].cells[3].paragraphs[0].runs[0]
            recovery_duration = table.rows[-1].cells[3].paragraphs[0].runs[0]

        self.assertEqual(activity_duration.font.color.rgb, RGBColor(192, 0, 0))
        self.assertIsNone(final_duration.font.color.rgb)
        self.assertIsNone(recovery_duration.font.color.rgb)

    def test_clean_evaluation_space_name_removes_area_and_capacity(self):
        self.assertEqual(
            clean_evaluation_space_name(
                "Aula de gestión de 45 m2 (para 15 alumnos) o de 60 m2 (para 25 alumnos)"
            ),
            "Aula de gestión",
        )


if __name__ == "__main__":
    unittest.main()
