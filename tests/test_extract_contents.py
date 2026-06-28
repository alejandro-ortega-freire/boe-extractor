import unittest

from source.extract_contents import parse_content_line, reset_content_state

from tests.helpers import (
    MAMD0309_PDF,
    find_training_module,
    find_uf,
    flatten_bullets,
    payload_for,
    require_pdf,
)


class ExtractContentsTests(unittest.TestCase):
    def test_semicolon_inline_subitems_keep_content_hierarchy(self):
        target = []
        state = reset_content_state()

        lines = [
            {
                "text": "1. Aplicaciones de tratamiento de imágenes en proyectos de construcción.",
                "x0": 117.2,
            },
            {
                "text": "- Gestión de formatos de importación y exportación.",
                "x0": 134.6,
            },
            {
                "text": "- Estructura de dibujos: píxeles, entidades, sólidos, bloques, objetos, capas;",
                "x0": 134.6,
            },
            {
                "text": "gestión de capas; gestión de versiones; historial.",
                "x0": 152.6,
            },
        ]

        for line in lines:
            state = parse_content_line(line, target, state)

        structure = target[0]["bullets"][1]

        self.assertEqual(structure["text"], "Estructura de dibujos:")
        self.assertEqual(
            [child["text"] for child in structure["children"]],
            [
                "píxeles, entidades, sólidos, bloques, objetos, capas.",
                "gestión de capas.",
                "gestión de versiones.",
                "historial.",
            ],
        )

    def test_black_square_markers_become_sibling_child_bullets(self):
        target = []
        state = reset_content_state()

        lines = [
            {
                "text": "3. Marco jurídico y contratación en el comercio e intermediación comercial.",
                "x0": 117.2,
            },
            {
                "text": "- Concepto y normas que rigen el comercio en el contexto jurídico:",
                "x0": 153.2,
            },
            {
                "text": "■ Comercio interior ■ Comercio internacional",
                "x0": 180.2,
            },
        ]

        for line in lines:
            state = parse_content_line(line, target, state)

        parent = target[0]["bullets"][0]

        self.assertEqual(parent["text"], "Concepto y normas que rigen el comercio en el contexto jurídico:")
        self.assertEqual(
            [child["text"] for child in parent["children"]],
            ["Comercio interior", "Comercio internacional"],
        )

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
