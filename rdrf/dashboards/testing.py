from django.test import TestCase
from dashboards.score_functions import sgc_symptom_score as f

from unittest.mock import Mock


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


class VisualisationsTestCase(TestCase):
    databases = {"default", "clinical"}
    fixtures = ["testing_auth", "testing_users", "testing_rdrf"]


class CRCTrafficLightTestCase(VisualisationsTestCase):
    def test_normal_case(self):
        initial_df = self.create_dataframe()
        tl = self.create_traffic_light(initial_df)

        table_data = tl._get_table_data()

        self.check_baseline(table_data)

        self.check_followups(table_data)

    def create_traffic_light(self, data):
        from dashboards.components.tl import TrafficLights

        vis_config = Mock()

        data = None
        patient = Mock()

        return TrafficLights("crc test tl", vis_config, data, patient, None)

    def create_dataframe(self):
        return None

    def check_baseline(self, df):
        num_baselines = 0

        for index, row in df.iterrows():
            if row["TYPE"] == "baseline":
                self.assertEqual(row["SEQ"], 0, "baseline row does not have SEQ 0")
                num_baselines += 1

        self.assertEqual(num_baselines, 1, f"Number of baseline rows is not 1: is {num_baselines}")


    def check_followups(self, df):
        for index, row in df.iterrows():
            if row["TYPE"] == "followup":
                seq = row["SEQ"]
                self.assertGreater(seq, 0, f"followup seq number should be greater than 0. Actual={seq}")
