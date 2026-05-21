import unittest

from source.cleaning import clean_line, clean_text
from source.extract_spaces import clean_space_name
from source.normalization import normalize_text


class CleaningTests(unittest.TestCase):
    def test_removes_space_before_punctuation(self):
        self.assertEqual(
            clean_line("Mesa y silla para formador ."),
            "Mesa y silla para formador."
        )

    def test_removes_residual_dot_from_space_name(self):
        self.assertEqual(
            clean_space_name("Aula de gestión."),
            "Aula de gestión"
        )

    def test_removes_textual_bullet_marker(self):
        self.assertEqual(
            normalize_text("○ Concepto de activo intangible."),
            "Concepto de activo intangible."
        )

    def test_normalization_removes_xml_control_characters(self):
        self.assertEqual(
            normalize_text("Texto\x00 válido"),
            "Texto válido"
        )

    def test_removes_old_boe_footer_when_embedded_in_line(self):
        self.assertEqual(
            clean_line(
                "CE3.4 Seleccionar máquinas electro-portátiles. BOE núm. 307 Lunes 22 diciembre 2008 51503"
            ),
            "CE3.4 Seleccionar máquinas electro-portátiles."
        )

    def test_removes_old_boe_header_when_embedded_in_line(self):
        self.assertEqual(
            clean_line(
                "CE2.3 Otros datos necesarios. 51502 Lunes 22 diciembre 2008 BOE núm. 307"
            ),
            "CE2.3 Otros datos necesarios."
        )

    def test_discards_old_boe_date_fragment_as_space_name(self):
        self.assertEqual(clean_space_name("Lunes diciembre"), "")


if __name__ == "__main__":
    unittest.main()
