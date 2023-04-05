from django.test import TestCase
from dashboards.score_functions import sgc_symptom_score as f


class VisTestCase(TestCase):
    def test_scg_symptom1(self):

        range_value = 3.0
        EORTCQLQC30_Q09 = 1.0
        EORTCQLQC30_Q19 = 2.0

        raw_scores = [EORTCQLQC30_Q09, EORTCQLQC30_Q19]
        raw_score = sum(raw_scores) / 2.0

        correct_value = 16.67

        result = f(raw_score, range_value)

        self.assertEquals(
            result,
            correct_value,
            f"symptom score: correct={correct_value} actual={result}",
        )

    def test_scg_symptom2(self):
        range_value = 3.0
        raw_score = None
        correct_value = None

        result = f(raw_score, range_value)

        self.assertEquals(
            result,
            correct_value,
            f"symptom score: correct={correct_value} actual={result}",
        )
