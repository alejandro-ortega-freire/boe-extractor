import unittest
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch

from source.models import BasicData, DocumentPayload, TrainingModule
from source.pipeline import process_pdf


class PipelineTests(unittest.TestCase):
    def test_process_pdf_groups_annexes_by_folder(self):
        payload = DocumentPayload(
            data=BasicData(codigo="TEST0101"),
            duration_text="10 horas",
            training_modules=[
                TrainingModule(identifier="MF0001_1: Primer módulo")
            ],
        )

        config = {
            "session_hours": 5,
            "start_date": None,
            "custom_holidays": {},
            "teacher_name": "Docente",
            "copy_subcriteria": False,
        }

        with TemporaryDirectory() as tmp:
            with (
                patch("source.pipeline.OUTPUT_FOLDER", tmp),
                patch("source.pipeline.build_payload", return_value=payload),
                patch("source.pipeline.calculate_schedule", return_value={}),
                patch("source.pipeline.create_info_docx"),
                patch("source.pipeline.create_anexo_iii_docx"),
                patch("source.pipeline.create_anexo_vi_docx"),
                patch("source.pipeline.create_anexo_iv_docx"),
                patch("source.pipeline.create_anexo_v_docx"),
            ):
                generated_files = process_pdf("input/TEST0101.pdf", config)

            certificate_folder = Path(tmp) / "TEST0101"
            anexo_iii_folder = certificate_folder / "Anexo III"
            anexo_iv_folder = certificate_folder / "Anexos IV"
            anexo_v_folder = certificate_folder / "Anexos V"
            anexo_vi_folder = certificate_folder / "Anexo VI"

            self.assertTrue(anexo_iii_folder.is_dir())
            self.assertTrue(anexo_iv_folder.is_dir())
            self.assertTrue(anexo_v_folder.is_dir())
            self.assertTrue(anexo_vi_folder.is_dir())
            self.assertIn(
                str(anexo_iii_folder / "anexoIII_TEST0101.docx"),
                generated_files,
            )
            self.assertIn(
                str(anexo_iv_folder / "anexoIV_MF0001_1_TEST0101.docx"),
                generated_files,
            )
            self.assertIn(
                str(anexo_v_folder / "anexoV_MF0001_1_TEST0101.docx"),
                generated_files,
            )
            self.assertIn(
                str(anexo_vi_folder / "anexoVI_TEST0101.docx"),
                generated_files,
            )


if __name__ == "__main__":
    unittest.main()
