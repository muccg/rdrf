from django.test import TestCase
from dashboards.score_functions import sgc_symptom_score as f

from unittest.mock import Mock
import pandas as pd


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


# class BCTrafficLightTestCase(TestCase):
#     def test_normal_case(self):
#         # normal data baseline + followups
#         initial_df = self.create_dataframe("normal")
#         expected_df = self.get_expected_dataframe("normal")
#         self.check(initial_df, expected_df)

#     def check(self, initial_df, expected_df):
#         tl = self.create_traffic_light(initial_df)
#         table_data = tl._get_table_data()
#         self.check_baseline(table_data)
#         self.check_followups(table_data)
#         self.check_dataframe(table_data, expected_df)

#     def test_missing_baseline(self):
#         initial_df = self.create_dataframe("missingbaseline")
#         expected_df = self.get_expected_dataframe("missingbaseline")
#         self.check(initial_df, expected_df)

#     def test_missing_sixmonth(self):
#         initial_df = self.create_dataframe("missingsixmonth")
#         expected_df = self.get_expected_dataframe("missingsixmonth")
#         self.check(initial_df, expected_df)

#     def test_missing_oneyear(self):
#         initial_df = self.create_dataframe("missingoneyear")
#         expected_df = self.get_expected_dataframe("missingoneyear")
#         self.check(initial_df, expected_df)

#     def create_traffic_light(self, data):
#         from dashboards.components.tl import TrafficLights
#         from dashboards.components.tl import get_fields

#         vis_config = Mock()

#         config_dict = {
#             "fields": [
#                 "EORTCQLQC30_Q01",
#                 "EORTCQLQC30_Q02",
#                 "EORTCQLQC30_Q03",
#                 "EORTCQLQC30_Q04",
#                 "EORTCQLQC30_Q05",
#                 "EORTCQLQC30_Q06",
#                 "EORTCQLQC30_Q07",
#                 "EORTCQLQC30_Q08",
#                 "EORTCQLQC30_Q09",
#                 "EORTCQLQC30_Q10",
#                 "EORTCQLQC30_Q11",
#                 "EORTCQLQC30_Q12",
#                 "EORTCQLQC30_Q13",
#                 "EORTCQLQC30_Q14",
#                 "EORTCQLQC30_Q15",
#                 "EORTCQLQC30_Q16",
#                 "EORTCQLQC30_Q17",
#                 "EORTCQLQC30_Q18",
#                 "EORTCQLQC30_Q19",
#                 "EORTCQLQC30_Q20",
#                 "EORTCQLQC30_Q21",
#                 "EORTCQLQC30_Q22",
#                 "EORTCQLQC30_Q23",
#                 "EORTCQLQC30_Q24",
#                 "EORTCQLQC30_Q25",
#                 "EORTCQLQC30_Q26",
#                 "EORTCQLQC30_Q27",
#                 "EORTCQLQC30_Q28",
#             ]
#         }

#         vis_config.config = config_dict
#         patient = Mock()

#         tl = TrafficLights("crc test tl", vis_config, data, patient, None)
#         tl.fields = get_fields(tl.config)
#         return tl

#     def create_dataframe(self, scenario):
#         csv_file_name = f"bc-{scenario}-initial.csv"
#         csv_file_path = f"/???/{csv_file_name}"
#         return pd.read_csv(csv_file_path)

#     def check_baseline(self, df):
#         num_baselines = 0
#         for index, row in df.iterrows():
#             if row["TYPE"] == "baseline":
#                 self.assertEqual(row["SEQ"], 0, "baseline row does not have SEQ 0")
#                 num_baselines += 1

#         self.assertEqual(
#             num_baselines, 1, f"Number of baseline rows is not 1: is {num_baselines}"
#         )

#     def check_followups(self, df):
#         for index, row in df.iterrows():
#             if row["TYPE"] == "followup":
#                 seq = row["SEQ"]
#                 self.assertGreater(
#                     seq,
#                     0,
#                     f"followup seq number should be greater than 0. Actual={seq}",
#                 )
