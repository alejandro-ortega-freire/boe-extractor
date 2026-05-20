import unittest

from source.content_assignment import assign_contents_to_criteria
from source.models import Bullet, ContentItem, Criterion


class ContentAssignmentTests(unittest.TestCase):
    def test_single_criterion_receives_all_contents(self):
        criteria = [Criterion(text="C1: Identificar conceptos")]
        contents = [
            ContentItem(title="1. Conceptos", bullets=[Bullet(text="Definición")]),
            ContentItem(title="2. Procedimientos", bullets=[Bullet(text="Aplicación")]),
        ]

        assigned = assign_contents_to_criteria(criteria, contents)

        self.assertEqual(len(assigned), 1)
        self.assertEqual([content.title for content in assigned[0]], ["1. Conceptos", "2. Procedimientos"])

    def test_no_criterion_is_left_empty_when_content_can_be_split(self):
        criteria = [
            Criterion(text="C1: Identificar conceptos"),
            Criterion(text="C2: Aplicar procedimientos"),
            Criterion(text="C3: Evaluar resultados"),
        ]
        contents = [
            ContentItem(
                title="1. Bloque amplio",
                bullets=[
                    Bullet(text="Identificación de conceptos."),
                    Bullet(text="Aplicación de procedimientos."),
                    Bullet(text="Evaluación de resultados."),
                ],
            )
        ]

        assigned = assign_contents_to_criteria(criteria, contents)

        self.assertEqual(len(assigned), len(criteria))
        self.assertTrue(all(group for group in assigned))
        self.assertEqual(
            [group[0].title for group in assigned],
            ["1. Bloque amplio (I)", "1. Bloque amplio (II)", "1. Bloque amplio (III)"]
        )

    def test_dict_callers_still_receive_dicts(self):
        criteria = [{"text": "C1: Identificar conceptos", "subcriteria": []}]
        contents = [{"title": "1. Conceptos", "bullets": [{"text": "Definición", "children": []}]}]

        assigned = assign_contents_to_criteria(criteria, contents)

        self.assertIsInstance(assigned[0][0], dict)


if __name__ == "__main__":
    unittest.main()
