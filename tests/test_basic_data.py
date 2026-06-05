import unittest

from source.basic_data import extract_basic_data


class BasicDataTests(unittest.TestCase):
    def test_familia_profesional_label_is_case_insensitive(self):
        data = extract_basic_data(
            "\n".join([
                "Denominación: Gestión contable y gestión administrativa para auditoría.",
                "Código: ADGD0108.",
                "Familia Profesional: Administración y gestión.",
                "Área profesional: Administración y auditoría.",
                "Nivel de cualificación profesional: 3.",
            ])
        )

        self.assertEqual(data["familia"], "Administración y gestión.")


if __name__ == "__main__":
    unittest.main()
