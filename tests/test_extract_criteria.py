import unittest

from source.extract_criteria import get_page_lines, is_contents_title, is_criterion_start

from tests.helpers import MAMD0309_PDF, find_training_module, find_uf, payload_for, require_pdf


class ExtractCriteriaTests(unittest.TestCase):
    def test_detects_criterion_start_with_or_without_colon(self):
        self.assertTrue(is_criterion_start("C1: Manejar programas informáticos"))
        self.assertTrue(is_criterion_start("C2 Manejar programas informáticos"))
        self.assertFalse(is_criterion_start("CE1.1 Manejar programas informáticos"))

    def test_contents_title_does_not_match_content_bullet_text(self):
        self.assertTrue(is_contents_title("Contenidos"))
        self.assertFalse(is_contents_title("Contenidos básicos, sistemas de presentación de memorias."))

    def test_page_lines_split_same_y_text_from_two_columns(self):
        class Page:
            def get_text(self, kind):
                if kind != "words":
                    raise AssertionError(kind)

                return [
                    (50, 100, 95, 110, "Contenidos"),
                    (340, 100, 385, 110, "Código:"),
                    (390, 100, 440, 110, "UF0195"),
                ]

        lines = get_page_lines(Page())

        self.assertEqual([line["text"] for line in lines], ["Contenidos", "Código: UF0195"])

    def test_mamd0309_uf1186_has_criteria(self):
        require_pdf(self, MAMD0309_PDF)
        payload = payload_for("MAMD0309.pdf")
        uf1186 = find_uf(find_training_module(payload, "MF0175_3"), "UF1186")

        self.assertEqual(len(uf1186.criteria), 2)
        self.assertTrue(uf1186.criteria[0].text.startswith("C1:"))
        self.assertTrue(uf1186.criteria[1].text.startswith("C2:"))


if __name__ == "__main__":
    unittest.main()
