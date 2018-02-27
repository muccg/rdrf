from rdrf.helpers.utils import TimeStripper
from rdrf.helpers.utils import HistoryTimeStripper
from django.test import TestCase
from copy import deepcopy


class FakeClinicalData(object):
    def __init__(self, pk, data):
        self.pk = pk
        self.data = data

    def save(self):
        print("Fake ClinicalData save called")


class TimeStripperTestCase(TestCase):
    def setUp(self):
        super(TimeStripperTestCase, self).setUp()

        self.data_with_date_cdes = {'django_model': 'Patient',
                                    'ClinicalData_timestamp': '2017-02-14T10:23:10.601182',
                                    'context_id': 4,
                                    'django_id': 3,
                                    'forms': [{'name': 'ClinicalData',
                                               'sections': [{'code': 'fhDateSection', 'allow_multiple': False,
                                                             'cdes': [{'value': 'fh_is_index', 'code': 'CDEIndexOrRelative'},
                                                                      {'value': '1972-06-15T00:00:00.00', 'code': 'DateOfAssessment'},
                                                                      {'value': '2015-01-05T10:23:10.601182', 'code': 'FHconsentDate'}]},
                                                            {'code': 'SEC0007', 'allow_multiple': False,
                                                             'cdes': [{'value': '', 'code': 'CDE00024'},
                                                                      {'value': '', 'code': 'CDEfhDutchLipidClinicNetwork'}]}]}]}

        self.copy_of_initial_data = deepcopy(self.data_with_date_cdes)

        self.data_without_date_cdes = {'django_model': 'Patient',
                                       'ClinicalData_timestamp': '2017-02-14T10:23:10.601182',
                                       'context_id': 40,
                                       'django_id': 300,
                                       'forms': [{'name': 'ClinicalData',
                                                  'sections': [{'code': 'fhDateSection', 'allow_multiple': False,
                                                                 'cdes': [{'value': 'fh_is_index', 'code': 'CDEIndexOrRelative'}]},
                                                               {'code': 'SEC0007', 'allow_multiple': False,
                                                                'cdes': [{'value': '', 'code': 'CDE00024'},
                                                                         {'value': '', 'code': 'CDEfhDutchLipidClinicNetwork'}]}]}]}

        self.m1 = FakeClinicalData(1, self.data_with_date_cdes)
        self.m2 = FakeClinicalData(2, self.data_without_date_cdes)

        self.ts = TimeStripper([self.m1, self.m2])
        self.ts.test_mode = True
        self.ts.date_cde_codes = ['DateOfAssessment', 'FHconsentDate']

    def test_timestripper(self):
        expected_date_of_assessment = "1972-06-15"
        expected_fh_consent_date = "2015-01-05"
        expected = [expected_date_of_assessment, expected_fh_consent_date]
        clinicaldata_timestamp_before = self.data_with_date_cdes["ClinicalData_timestamp"]
        fh_index_before = self.data_with_date_cdes["forms"][0]["sections"][0]["cdes"][0]["value"]

        self.ts.forward()
        clinicaldata_timestamp_after = self.data_with_date_cdes["ClinicalData_timestamp"]
        fh_index_after = self.data_with_date_cdes["forms"][0]["sections"][0]["cdes"][0]["value"]

        self.assertTrue(self.ts.converted_date_cdes == expected,
                        "Expected %s Actual %s" % (expected, self.ts.converted_date_cdes))

        value1 = self.data_with_date_cdes["forms"][0]["sections"][0]["cdes"][1]["value"]
        self.assertTrue(value1 == expected_date_of_assessment,
                        "DateOfAssessment value not modified by TimeStripper")
        value2 = self.data_with_date_cdes["forms"][0]["sections"][0]["cdes"][2]["value"]
        self.assertTrue(value2 == expected_fh_consent_date,
                        "FHConsentdate value not modified by TimeStripper")

        self.assertTrue(clinicaldata_timestamp_after == clinicaldata_timestamp_before,
                        "Timestamps which are not date cdes should not be affected by TimeStripper")
        self.assertTrue(fh_index_before == fh_index_after,
                        "Non date cdes should not be affected by TimeStripper")

    def test_update_of_multisections(self):
        # multisection with 2 items , one cde Surgery , another SurgeryDate
        cde_dict1 = {"code": "Surgery", "value": "Appendix Removed"}
        cde_dict2 = {"code": "SurgeryDate", "value": "2017-02-14T00:00:00"}
        cde_dict3 = {"code": "Surgery", "value": "Stomach Ulcer"}
        cde_dict4 = {"code": "SurgeryDate", "value": "2018-03-26T00:00:00"}
        # assume last item ok
        cde_dict5 = {"code": "Surgery", "value": "Heart Surgery"}
        cde_dict6 = {"code": "SurgeryDate", "value": "2011-11-05"}

        item1 = [cde_dict1, cde_dict2]
        item2 = [cde_dict3, cde_dict4]
        item3 = [cde_dict5, cde_dict6]

        multisection = {"allow_multiple": True,
                        "cdes": [item1, item2, item3]}

        data_with_multisections = {"forms": [{"form": "testing",
                                              "sections": [multisection]}]}

        m = FakeClinicalData(23, data_with_multisections)

        ts = TimeStripper([m])
        ts.test_mode = True
        ts.date_cde_codes = ['SurgeryDate']

        ts.forward()

        self.assertTrue(ts.converted_date_cdes == ["2017-02-14", "2018-03-26"],
                        "Multisection timestrip failed: actual = %s" % ts.converted_date_cdes)

        expected_value1 = "2017-02-14"
        actual_value1 = m.data["forms"][0]["sections"][0]["cdes"][0][1]["value"]
        self.assertEqual(
            expected_value1,
            actual_value1,
            "Update of multisection failed for first item: actual = %s" %
            actual_value1)

        expected_value2 = "2018-03-26"
        actual_value2 = m.data["forms"][0]["sections"][0]["cdes"][1][1]["value"]
        self.assertEqual(
            expected_value2,
            actual_value2,
            "Update of multisection failed for second item: actual = %s" %
            actual_value2)

        expected_value3 = "2011-11-05"  # n shouldn't have changed
        actual_value3 = m.data["forms"][0]["sections"][0]["cdes"][2][1]["value"]
        self.assertEqual(
            expected_value3,
            actual_value3,
            "Update of multisection failed for third item: actual = %s" %
            actual_value3)

    def test_history_munging(self):
        history_modjgo_data = {"django_id": 1,
                               "record": {
                                   "django_id": 1,
                                   "timestamp": "2017-02-13T12:28:49.355839",
                                   "forms": [
                                       {
                                           "sections": [
                                                {
                                                    "allow_multiple": False,
                                                    "cdes": [
                                                        {
                                                            "value": "fh_is_index",
                                                            "code": "CDEIndexOrRelative"
                                                        },
                                                        {
                                                            "value": "2017-02-15",
                                                            "code": "DateOfAssessment"
                                                        },
                                                        {
                                                            "value": "2017-02-14T00:00:00.000",
                                                            "code": "FHconsentDate"
                                                        }
                                                    ],
                                                    "code": "fhDateSection"
                                                },
                                               {
                                                    "allow_multiple": False,
                                                    "cdes": [
                                                        {
                                                            "value": "",
                                                            "code": "CDE00024"
                                                        },
                                                        {
                                                            "value": "",
                                                            "code": "CDEfhDutchLipidClinicNetwork"
                                                        }
                                                    ],
                                                    "code": "SEC0007"
                                                },
                                               {
                                                    "allow_multiple": False,
                                                    "cdes": [
                                                        {
                                                            "value": "fh2_y",
                                                            "code": "CDE00004"
                                                        },
                                                        {
                                                            "value": "fh2_n",
                                                            "code": "FHFamHistTendonXanthoma"
                                                        },
                                                        {
                                                            "value": "fh2_n",
                                                            "code": "FHFamHistArcusCornealis"
                                                        },
                                                        {
                                                            "value": "fh2_y",
                                                            "code": "CDE00003"
                                                        },
                                                        {
                                                            "value": "y_childunder18",
                                                            "code": "FHFamilyHistoryChild"
                                                        }
                                                    ],
                                                    "code": "SEC0002"
                                                },
                                               {
                                                    "allow_multiple": False,
                                                    "cdes": [
                                                        {
                                                            "value": "",
                                                            "code": "FHSupravalvularDisease"
                                                        },
                                                        {
                                                            "value": None,
                                                            "code": "FHAgeAtMI"
                                                        },
                                                        {
                                                            "value": None,
                                                            "code": "FHAgeAtCV"
                                                        },
                                                        {
                                                            "value": "",
                                                            "code": "FHPremNonCoronary"
                                                        },
                                                        {
                                                            "value": "",
                                                            "code": "FHAorticValveDisease"
                                                        },
                                                        {
                                                            "value": "fh2_n",
                                                            "code": "FHPersHistCerebralVD"
                                                        },
                                                        {
                                                            "value": "fhpremcvd_unknown",
                                                            "code": "CDE00011"
                                                        },
                                                        {
                                                            "value": "",
                                                            "code": "FHCoronaryRevasc"
                                                        },
                                                        {
                                                            "value": "",
                                                            "code": "FHMyocardialInfarction"
                                                        }
                                                    ],
                                                    "code": "SEC0004"
                                                },
                                               {
                                                    "allow_multiple": False,
                                                    "cdes": [
                                                        {
                                                            "value": "u_",
                                                            "code": "CDE00002"
                                                        },
                                                        {
                                                            "value": "",
                                                            "code": "FHXanthelasma"
                                                        },
                                                        {
                                                            "value": "y",
                                                            "code": "CDE00001"
                                                        }
                                                    ],
                                                    "code": "SEC0001"
                                                },
                                               {
                                                    "allow_multiple": False,
                                                    "cdes": [
                                                        {
                                                            "value": "",
                                                            "code": "PlasmaLipidTreatment"
                                                        },
                                                        {
                                                            "value": None,
                                                            "code": "CDE00019"
                                                        },
                                                        {
                                                            "value": "NaN",
                                                            "code": "LDLCholesterolAdjTreatment"
                                                        },
                                                        {
                                                            "value": None,
                                                            "code": "CDE00013"
                                                        }
                                                    ],
                                                    "code": "FHLDLforFHScore"
                                                },
                                               {
                                                    "allow_multiple": True,
                                                    "cdes": [
                                                        [
                                                            {
                                                                "value": None,
                                                                "code": "CDE00014"
                                                            },
                                                            {
                                                                "value": None,
                                                                "code": "FHLipidProfileUntreatedDate"
                                                            },
                                                            {
                                                                "value": None,
                                                                "code": "FHAlbum"
                                                            },
                                                            {
                                                                "value": None,
                                                                "code": "CDE00012"
                                                            },
                                                            {
                                                                "value": None,
                                                                "code": "FHCK"
                                                            },
                                                            {
                                                                "value": None,
                                                                "code": "FHA1"
                                                            },
                                                            {
                                                                "value": "",
                                                                "code": "PlasmaLipidTreatmentNone"
                                                            },
                                                            {
                                                                "value": None,
                                                                "code": "FHAST"
                                                            },
                                                            {
                                                                "value": None,
                                                                "code": "CDE00015"
                                                            },
                                                            {
                                                                "value": None,
                                                                "code": "FHApoB"
                                                            },
                                                            {
                                                                "value": None,
                                                                "code": "FHALT"
                                                            },
                                                            {
                                                                "value": None,
                                                                "code": "FHLLDLconc"
                                                            },
                                                            {
                                                                "value": None,
                                                                "code": "FHCreatinine"
                                                            },
                                                            {
                                                                "value": "",
                                                                "code": "FHCompliance"
                                                            },
                                                            {
                                                                "value": "",
                                                                "code": "CDEfhOtherIntolerantDrug"
                                                            },
                                                            {
                                                                "value": None,
                                                                "code": "CDE00016"
                                                            },
                                                            {
                                                                "value": None,
                                                                "code": "FHCRP"
                                                            }
                                                        ]
                                                    ],
                                                    "code": "SEC0005"
                                                },
                                               {
                                                    "allow_multiple": False,
                                                    "cdes": [
                                                        {
                                                            "value": "NaN",
                                                            "code": "CDEBMI"
                                                        },
                                                        {
                                                            "value": "",
                                                            "code": "FHHypertriglycerd"
                                                        },
                                                        {
                                                            "value": None,
                                                            "code": "HbA1c"
                                                        },
                                                        {
                                                            "value": "",
                                                            "code": "FHHypothyroidism"
                                                        },
                                                        {
                                                            "value": None,
                                                            "code": "CDE00009"
                                                        },
                                                        {
                                                            "value": None,
                                                            "code": "FHHeartRate"
                                                        },
                                                        {
                                                            "value": None,
                                                            "code": "CDE00010"
                                                        },
                                                        {
                                                            "value": None,
                                                            "code": "FHWaistCirc"
                                                        },
                                                        {
                                                            "value": "",
                                                            "code": "FHObesity"
                                                        },
                                                        {
                                                            "value": None,
                                                            "code": "CDE00008"
                                                        },
                                                        {
                                                            "value": None,
                                                            "code": "CDEWeight"
                                                        },
                                                        {
                                                            "value": None,
                                                            "code": "FHPackYears"
                                                        },
                                                        {
                                                            "value": None,
                                                            "code": "CDEHeight"
                                                        },
                                                        {
                                                            "value": "",
                                                            "code": "CDE00007"
                                                        },
                                                        {
                                                            "value": "",
                                                            "code": "FHAlcohol"
                                                        },
                                                        {
                                                            "value": "",
                                                            "code": "CDE00005"
                                                        },
                                                        {
                                                            "value": "",
                                                            "code": "CDE00006"
                                                        },
                                                        {
                                                            "value": "",
                                                            "code": "FHCVDOther"
                                                        },
                                                        {
                                                            "value": None,
                                                            "code": "FHeGFR"
                                                        },
                                                        {
                                                            "value": "",
                                                            "code": "ChronicKidneyDisease"
                                                        },
                                                        {
                                                            "value": "",
                                                            "code": "FHHepaticSteatosis"
                                                        },
                                                        {
                                                            "value": None,
                                                            "code": "FHTSH"
                                                        }
                                                    ],
                                                    "code": "SEC0003"
                                                },
                                               {
                                                    "allow_multiple": True,
                                                    "cdes": [
                                                        [
                                                            {
                                                                "value": "",
                                                                "code": "FHTrialStatus"
                                                            },
                                                            {
                                                                "value": None,
                                                                "code": "FHTrialSTartDate"
                                                            },
                                                            {
                                                                "value": "",
                                                                "code": "FHClinicalTrialName"
                                                            },
                                                            {
                                                                "value": None,
                                                                "code": "FHTrialLength"
                                                            }
                                                        ]
                                                    ],
                                                    "code": "FHClinicalTrials"
                                                }
                                           ],
                                           "name": "ClinicalData"
                                       }
                                   ],
                                   "context_id": 1,
                                   "ClinicalData_timestamp": "2017-02-13T12:28:49.355839",
                                   "django_model": "Patient"
                               },
                               "record_type": "snapshot",
                               "timestamp": "2017-02-13 12:28:49.665333",
                               "registry_code": "fh",
                               "context_id": 1,
                               "django_model": "Patient"
                               }

        expected_dates = ['2017-02-14']
        history_record = FakeClinicalData(73, history_modjgo_data)
        ts = HistoryTimeStripper([history_record])
        ts.test_mode = True
        ts.date_cde_codes = ['FHconsentDate']
        ts.forward()

        self.assertTrue(ts.converted_date_cdes == expected_dates,
                        "Expected: %s, Actual: %s" % (expected_dates,
                                                      ts.converted_date_cdes))
