import unittest

from tests.helpers import (
    MAMD0309_PDF,
    find_training_module,
    find_uf,
    flatten_bullets,
    payload_for,
    require_pdf,
)


class ExtractContentsTests(unittest.TestCase):
    def test_mamd0309_uf1185_uf1186_uf1187_have_contents(self):
        require_pdf(self, MAMD0309_PDF)
        payload = payload_for("MAMD0309.pdf")
        mf0175 = find_training_module(payload, "MF0175_3")

        expected_counts = {
            "UF1185": 3,
            "UF1186": 4,
            "UF1187": 3,
        }

        for uf_code, expected_count in expected_counts.items():
            with self.subTest(uf=uf_code):
                self.assertEqual(len(find_uf(mf0175, uf_code).contents), expected_count)

    def test_mamd0309_sectoriales_is_not_split_as_child_bullet(self):
        require_pdf(self, MAMD0309_PDF)
        payload = payload_for("MAMD0309.pdf")
        uf1182 = find_uf(find_training_module(payload, "MF0174_3"), "UF1182")

        all_bullets = [
            text
            for content in uf1182.contents
            for text in flatten_bullets(content.bullets)
        ]

        self.assertIn(
            "Vaciado selectivo de revistas especializadas e información de novedades sectoriales.",
            all_bullets
        )
        self.assertNotIn("sectoriales.", all_bullets)


if __name__ == "__main__":
    unittest.main()
