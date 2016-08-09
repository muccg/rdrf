# -*- coding: utf-8 -*-
from selenium import selenium
from base import Base


class DynamicFormsetTest(Base):

    def test_dynamic_formset_add_remove(self):
        """
        This test adds various combinations of "multisections" to the clinical form and observes
        the contents after saving - actions such as:
            clicking Add on a multisection and adding data in each element
            clicking Add multiple times and ditto
            clicking Add and then clicking remove in middle then clicking add again
            It uses the version of the DM1 registry in the test fixture

        :return:
        """
        sel = self.selenium
        sel.open("/admin/")
        sel.type("id=id_username", "admin")
        sel.type("id=id_password", "admin")
        sel.click("css=input.btn.btn-success")
        sel.wait_for_page_to_load("30000")
        sel.open("/admin/patients/patient/")
        sel.wait_for_page_to_load("30000")
        sel.click("link=Add patient")

        sel.wait_for_page_to_load("30000")
        sel.click("id=id_consent")
        sel.click("id=id_consent_clinical_trials")
        sel.click("id=id_consent_sent_information")

        sel.remove_selection("id=id_rdrf_registry", "label=FH Registry (fh)")
        sel.add_selection("id=id_rdrf_registry", "label=Myotonic Dystrophy (DM1)")
        sel.add_selection("id=id_working_groups", "label=Western Australia")

        sel.type("id=id_family_name", "Hooh")
        sel.type("id=id_given_names", "Kevin")
        sel.select("id=id_sex", "label=Male")
        sel.click("css=img.ui-datepicker-trigger")
        sel.click("link=1")
        sel.click("name=_save")

        sel.wait_for_page_to_load("30000")
        sel.select("name=registry", "value=3")
        sel.click("css=input.btn.btn-success")
        sel.wait_for_page_to_load("30000")
        sel.click("id=data-modules-btn")
        sel.click("link=Clinical Data")
        sel.wait_for_page_to_load("30000")

        sel.select("id=id_ClinicalData____DM1Status____DM1Condition", "label=DM1")
        sel.select("id=id_ClinicalData____DM1Status____DM1AffectedStatus",
                   "label=Adult Myotonic Dystrophy")
        sel.select(
            "id=id_ClinicalData____DM1Status____DM1FirstSymptom", "label=Cardiac symptoms")
        sel.select("id=id_ClinicalData____DM1Status____DM1FirstSuspectedBy", "label=Self")
        sel.type("id=id_ClinicalData____DM1Status____AgeAtDiagnosis", "1")
        sel.type("id=id_ClinicalData____DM1Status____AgeAtMolecularDiagnosis", "1")
        sel.type("id=id_ClinicalData____DM1Status____AgeAtMolecularDiagnosis", "2")
        sel.select(
            "id=id_ClinicalData____DM1GeneticTestDetails____GeneticTestResultsAvailable",
            "label=Yes")
        sel.select(
            "id=id_ClinicalData____DM1GeneticTestDetails____HasReceivedGeneticCounselling",
            "label=Yes")
        sel.select(
            "id=id_ClinicalData____DM1GeneticTestDetails____FamReceivedGeneticCounselling",
            "label=Yes")
        sel.select("id=id_ClinicalData____DM1MotorFunction____CanWalk", "label=No")
        sel.select(
            "id=id_ClinicalData____DM1MotorFunction____WalkAssistanceDevice", "label=Walker")
        sel.type("id=id_ClinicalData____DM1MotorFunction____AgeStartedUsingDeviceWalking", "1")
        sel.select(
            "id=id_ClinicalData____DM1MotorFunction____DM1BestMotorLevel",
            "label=Non-ambulatory")
        sel.select("id=id_ClinicalData____DM1MotorFunction____WheelChairUse", "label=Unknown")
        sel.type("id=id_ClinicalData____DM1MotorFunction____WheelChairUseAge", "-1")
        sel.type("id=id_ClinicalData____DM1MotorFunction____WheelChairUseAge", "0")
        sel.type("id=id_ClinicalData____DM1MotorFunction____WheelChairUseAge", "1")
        sel.select(
            "id=id_ClinicalData____DM1MotorFunction____Dysarthria", "label=No dysarthria")
        sel.select("id=id_ClinicalData____DM1Muscle____Myotonia", "label=No")
        sel.select("id=id_ClinicalData____DM1Muscle____FacialWeakness", "label=No")
        sel.select("id=id_ClinicalData____DM1Muscle____DM1EarlyWeakness", "label=No")
        sel.select(
            "id=id_ClinicalData____DM1MRCScaleMuscleGrading____FlexorDigitorumProfundis",
            "label=1")
        sel.select(
            "id=id_ClinicalData____DM1MRCScaleMuscleGrading____TibialisAnterior", "label=2")
        sel.select("id=id_ClinicalData____DM1MRCScaleMuscleGrading____NeckFlexion", "label=3")
        sel.select("id=id_ClinicalData____DM1MRCScaleMuscleGrading____Iliopsoas", "label=4")
        sel.type(
            "id=id_formset_DM1MuscleMedications-0-ClinicalData____DM1MuscleMedications____Drug",
            "mm1")
        sel.select(
            "id=id_formset_DM1MuscleMedications-0-ClinicalData____DM1MuscleMedications____MuscleMedicationStatus",
            "label=Current prescription")
        sel.click("id=add_button_for_section_DM1MuscleMedications")
        sel.type(
            "id=id_formset_DM1MuscleMedications-1-ClinicalData____DM1MuscleMedications____Drug",
            "mm2")
        sel.select(
            "id=id_formset_DM1MuscleMedications-1-ClinicalData____DM1MuscleMedications____MuscleMedicationStatus",
            "label=Previous prescription")
        sel.click("id=add_button_for_section_DM1MuscleMedications")
        sel.type(
            "id=id_formset_DM1MuscleMedications-2-ClinicalData____DM1MuscleMedications____Drug",
            "mm3")
        sel.select(
            "id=id_formset_DM1MuscleMedications-2-ClinicalData____DM1MuscleMedications____MuscleMedicationStatus",
            "label=Current prescription")
        sel.select("id=id_ClinicalData____DM1Surgeries____CardiacImplant", "label=No")
        sel.select("id=id_ClinicalData____DM1Surgeries____CataractSurgery", "label=No")
        sel.click("id=id_ClinicalData____DM1Surgeries____CataractDiagnosis_1")
        sel.select("id=id_ClinicalData____DM1Heart____HeartCondition", "label=No")
        sel.type(
            "id=id_formset_DM1HeartMedications-0-ClinicalData____DM1HeartMedications____Drug",
            "hm1")
        sel.select(
            "id=id_formset_DM1HeartMedications-0-ClinicalData____DM1HeartMedications____HeartMedicationStatus",
            "label=Current prescription")
        sel.click("id=add_button_for_section_DM1HeartMedications")
        sel.type(
            "id=id_formset_DM1HeartMedications-1-ClinicalData____DM1HeartMedications____Drug",
            "hm2")
        sel.select(
            "id=id_formset_DM1HeartMedications-1-ClinicalData____DM1HeartMedications____HeartMedicationStatus",
            "label=Previous prescription")
        sel.click("id=add_button_for_section_DM1HeartMedications")
        sel.type(
            "id=id_formset_DM1HeartMedications-2-ClinicalData____DM1HeartMedications____Drug",
            "hm3")
        sel.select(
            "id=id_formset_DM1HeartMedications-2-ClinicalData____DM1HeartMedications____HeartMedicationStatus",
            "label=Current prescription")
        sel.click("xpath=(//button[@type='button'])[7]")
        sel.click("id=add_button_for_section_DM1HeartMedications")
        sel.type(
            "id=id_formset_DM1HeartMedications-2-ClinicalData____DM1HeartMedications____Drug",
            "hm4")
        sel.select(
            "xpath=(//select[@id='id_formset_DM1HeartMedications-2-ClinicalData____DM1HeartMedications____HeartMedicationStatus'])[2]",
            "label=Previous prescription")
        sel.select(
            "id=id_ClinicalData____DM1Respiratory____DM1NonInvasiveVentilation", "label=No")
        sel.type("id=id_ClinicalData____DM1Respiratory____AgeStartedVentilationDevice", "1")
        sel.select("id=id_ClinicalData____DM1Respiratory____VentilationType",
                   "label=Bi-level Positive Airway Pressure (BIPAP)")
        sel.select("id=id_ClinicalData____DM1Respiratory____DM1InvasiveVentilation", "label=No")
        sel.select("id=id_ClinicalData____DM1FeedingFunction____DM1Dysphagia", "label=No")
        sel.select(
            "id=id_ClinicalData____DM1FeedingFunction____DM1GastricNasalTube", "label=No")
        sel.select("id=id_ClinicalData____DM1Fatigue____DM1Fatigue", "label=No")
        sel.select("id=id_ClinicalData____DM1Fatigue____DM1FatigueSittingReading",
                   "label=High chance of dozing")
        sel.select("id=id_ClinicalData____DM1Fatigue____DM1FatigueTV",
                   "label=High chance of dozing")
        sel.select("id=id_ClinicalData____DM1Fatigue____DM1FatigueSittingInactive",
                   "label=High chance of dozing")
        sel.select("id=id_ClinicalData____DM1Fatigue____DM1FatiguePassenger",
                   "label=High chance of dozing")
        sel.select("id=id_ClinicalData____DM1Fatigue____DM1FatigueLying",
                   "label=High chance of dozing")
        sel.select("id=id_ClinicalData____DM1Fatigue____DM1FatigueSittingTalking",
                   "label=High chance of dozing")
        sel.select("id=id_ClinicalData____DM1Fatigue____DM1FatigueSittingQuietly",
                   "label=High chance of dozing")
        sel.select("id=id_ClinicalData____DM1Fatigue____DM1FatigueInCar",
                   "label=High chance of dozing")
        sel.type(
            "id=id_formset_DM1FatigueMedication-0-ClinicalData____DM1FatigueMedication____DM1FatigueDrug",
            "fm1")
        sel.select(
            "id=id_formset_DM1FatigueMedication-0-ClinicalData____DM1FatigueMedication____DM1FatigueDrugStatus",
            "label=Current prescription")
        sel.click("id=add_button_for_section_DM1FatigueMedication")
        sel.type(
            "id=id_formset_DM1FatigueMedication-1-ClinicalData____DM1FatigueMedication____DM1FatigueDrug",
            "fm2")
        sel.select(
            "id=id_formset_DM1FatigueMedication-1-ClinicalData____DM1FatigueMedication____DM1FatigueDrugStatus",
            "label=Previous prescription")
        sel.click("xpath=(//button[@type='button'])[10]")
        sel.select("id=id_ClinicalData____DM1SocioeconomicFactors____DM1Education",
                   "label=Special Education")
        sel.select(
            "id=id_ClinicalData____DM1SocioeconomicFactors____DM1Occupation", "label=Employed")
        sel.select(
            "id=id_ClinicalData____DM1SocioeconomicFactors____DM1EmploymentAffected",
            "label=No")
        sel.select(
            "id=id_ClinicalData____DM1GeneralMedicalFactors____DM1Diabetes",
            "label=Not diagnosed")
        sel.select(
            "id=id_ClinicalData____DM1GeneralMedicalFactors____DM1CancerOrTumor", "label=No")
        sel.click("id=id_ClinicalData____DM1GeneralMedicalFactors____DM1LiverDisease")
        sel.click("id=id_ClinicalData____DM1GeneralMedicalFactors____DM1Cholesterol")
        sel.select(
            "id=id_ClinicalData____DM1GeneralMedicalFactors____DM1CognitiveImpairment",
            "label=No")
        sel.select(
            "id=id_formset_DM1FamilyMembers-0-ClinicalData____DM1FamilyMembers____DM1Sex",
            "label=Male")
        sel.select(
            "id=id_formset_DM1FamilyMembers-0-ClinicalData____DM1FamilyMembers____DM1Relationship",
            "label=Parent")
        sel.select(
            "id=id_formset_DM1FamilyMembers-0-ClinicalData____DM1FamilyMembers____DM1FamilyDiagnosis",
            "label=DM1")
        sel.type(
            "id=id_formset_DM1FamilyMembers-0-ClinicalData____DM1FamilyMembers____DM1FamilyPatientRecord",
            "1")
        sel.click("id=add_button_for_section_DM1FamilyMembers")
        sel.select(
            "id=id_formset_DM1FamilyMembers-1-ClinicalData____DM1FamilyMembers____DM1Sex",
            "label=Female")
        sel.select(
            "id=id_formset_DM1FamilyMembers-1-ClinicalData____DM1FamilyMembers____DM1Relationship",
            "label=Sibling")
        sel.select(
            "id=id_formset_DM1FamilyMembers-1-ClinicalData____DM1FamilyMembers____DM1FamilyDiagnosis",
            "label=DM2")
        sel.type(
            "id=id_formset_DM1FamilyMembers-1-ClinicalData____DM1FamilyMembers____DM1FamilyPatientRecord",
            "2")
        sel.click("id=add_button_for_section_DM1FamilyMembers")
        sel.select(
            "id=id_formset_DM1FamilyMembers-2-ClinicalData____DM1FamilyMembers____DM1Sex",
            "label=Male")
        sel.select(
            "id=id_formset_DM1FamilyMembers-2-ClinicalData____DM1FamilyMembers____DM1Relationship",
            "label=Child")
        sel.select(
            "id=id_formset_DM1FamilyMembers-2-ClinicalData____DM1FamilyMembers____DM1FamilyDiagnosis",
            "label=Dont know")
        sel.type(
            "id=id_formset_DM1FamilyMembers-2-ClinicalData____DM1FamilyMembers____DM1FamilyPatientRecord",
            "3")
        sel.type(
            "id=id_formset_DM1ClinicalTrials-0-ClinicalData____DM1ClinicalTrials____DM1DrugName",
            "d1")
        sel.type(
            "id=id_formset_DM1ClinicalTrials-0-ClinicalData____DM1ClinicalTrials____DM1TrialName",
            "t1")
        sel.type(
            "id=id_formset_DM1ClinicalTrials-0-ClinicalData____DM1ClinicalTrials____DM1TrialSponsor",
            "s2")
        sel.type(
            "id=id_formset_DM1ClinicalTrials-0-ClinicalData____DM1ClinicalTrials____DM1TrialPhase",
            "p1")
        sel.type(
            "id=id_formset_DM1ClinicalTrials-0-ClinicalData____DM1ClinicalTrials____DM1TrialSponsor",
            "s1")
        sel.click("id=add_button_for_section_DM1ClinicalTrials")
        sel.type(
            "id=id_formset_DM1ClinicalTrials-1-ClinicalData____DM1ClinicalTrials____DM1DrugName",
            "d2")
        sel.type(
            "id=id_formset_DM1ClinicalTrials-1-ClinicalData____DM1ClinicalTrials____DM1TrialName",
            "t2")
        sel.type(
            "id=id_formset_DM1ClinicalTrials-1-ClinicalData____DM1ClinicalTrials____DM1TrialSponsor",
            "s2")
        sel.type(
            "id=id_formset_DM1ClinicalTrials-1-ClinicalData____DM1ClinicalTrials____DM1TrialPhase",
            "p2")
        sel.click("xpath=(//button[@type='button'])[16]")
        sel.click("id=add_button_for_section_DM1ClinicalTrials")
        sel.type(
            "id=id_formset_DM1ClinicalTrials-1-ClinicalData____DM1ClinicalTrials____DM1DrugName",
            "d3")
        sel.type(
            "id=id_formset_DM1ClinicalTrials-1-ClinicalData____DM1ClinicalTrials____DM1TrialName",
            "t3")
        sel.type(
            "id=id_formset_DM1ClinicalTrials-1-ClinicalData____DM1ClinicalTrials____DM1TrialSponsor",
            "s3")
        sel.type(
            "id=id_formset_DM1ClinicalTrials-1-ClinicalData____DM1ClinicalTrials____DM1TrialPhase",
            "p3")
        sel.type(
            "id=id_formset_DM1OtherRegistry-0-ClinicalData____DM1OtherRegistry____DM1OtherRegistry",
            "r1")
        sel.click("id=add_button_for_section_DM1OtherRegistry")
        sel.type(
            "id=id_formset_DM1OtherRegistry-1-ClinicalData____DM1OtherRegistry____DM1OtherRegistry",
            "r2")
        sel.click("id=add_button_for_section_DM1OtherRegistry")
        sel.type(
            "id=id_formset_DM1OtherRegistry-2-ClinicalData____DM1OtherRegistry____DM1OtherRegistry",
            "r3")
        sel.click("id=add_button_for_section_DM1OtherRegistry")
        sel.type(
            "id=id_formset_DM1OtherRegistry-3-ClinicalData____DM1OtherRegistry____DM1OtherRegistry",
            "r4")
        sel.click("id=add_button_for_section_DM1OtherRegistry")
        sel.type(
            "id=id_formset_DM1OtherRegistry-4-ClinicalData____DM1OtherRegistry____DM1OtherRegistry",
            "r5")
        sel.click("xpath=(//button[@type='button'])[20]")
        sel.click("id=add_button_for_section_DM1OtherRegistry")
        sel.type(
            "id=id_formset_DM1OtherRegistry-4-ClinicalData____DM1OtherRegistry____DM1OtherRegistry",
            "r6")
        sel.type("id=id_ClinicalData____DM1Notes____DM1Notes", "yay")
        sel.click("css=input.btn.btn-info")
        sel.wait_for_page_to_load("30000")
        try:
            self.assertEqual(u"× Patient Kevin HOOH saved successfully",
                             sel.get_text("//div[@id='suit-center']/div[2]"))
        except AssertionError as e:
            self.verificationErrors.append(str(e))
        try:
            self.assertEqual(
                "mm1",
                sel.get_value("id=id_formset_DM1MuscleMedications-0-ClinicalData____DM1MuscleMedications____Drug"))
        except AssertionError as e:
            self.verificationErrors.append(str(e))
        try:
            self.assertEqual("Current prescription", sel.get_text(
                "id=id_formset_DM1MuscleMedications-0-ClinicalData____DM1MuscleMedications____MuscleMedicationStatus"))
        except AssertionError as e:
            self.verificationErrors.append(str(e))
        try:
            self.assertEqual(
                "mm2",
                sel.get_value("id=id_formset_DM1MuscleMedications-1-ClinicalData____DM1MuscleMedications____Drug"))
        except AssertionError as e:
            self.verificationErrors.append(str(e))
        try:
            self.assertEqual("Previous prescription", sel.get_text(
                "id=id_formset_DM1MuscleMedications-1-ClinicalData____DM1MuscleMedications____MuscleMedicationStatus"))
        except AssertionError as e:
            self.verificationErrors.append(str(e))
        try:
            self.assertEqual(
                "mm3",
                sel.get_value("id=id_formset_DM1MuscleMedications-2-ClinicalData____DM1MuscleMedications____Drug"))
        except AssertionError as e:
            self.verificationErrors.append(str(e))
        try:
            self.assertEqual("Current prescription", sel.get_text(
                "id=id_formset_DM1MuscleMedications-2-ClinicalData____DM1MuscleMedications____MuscleMedicationStatus"))
        except AssertionError as e:
            self.verificationErrors.append(str(e))
        try:
            self.assertEqual(
                "hm1",
                sel.get_value("id=id_formset_DM1HeartMedications-0-ClinicalData____DM1HeartMedications____Drug"))
        except AssertionError as e:
            self.verificationErrors.append(str(e))
        try:
            self.assertEqual(
                "hm4",
                sel.get_value("id=id_formset_DM1HeartMedications-2-ClinicalData____DM1HeartMedications____Drug"))
        except AssertionError as e:
            self.verificationErrors.append(str(e))
        try:
            self.assertEqual("Previous prescription", sel.get_text(
                "id=id_formset_DM1HeartMedications-2-ClinicalData____DM1HeartMedications____HeartMedicationStatus"))
        except AssertionError as e:
            self.verificationErrors.append(str(e))
        try:
            self.assertEqual("fm2", sel.get_value(
                "id=id_formset_DM1FatigueMedication-0-ClinicalData____DM1FatigueMedication____DM1FatigueDrug"))
        except AssertionError as e:
            self.verificationErrors.append(str(e))
        try:
            self.assertEqual("Previous prescription", sel.get_text(
                "id=id_formset_DM1FatigueMedication-0-ClinicalData____DM1FatigueMedication____DM1FatigueDrugStatus"))
        except AssertionError as e:
            self.verificationErrors.append(str(e))
        try:
            self.assertEqual("Male", sel.get_text(
                "id=id_formset_DM1FamilyMembers-0-ClinicalData____DM1FamilyMembers____DM1Sex"))
        except AssertionError as e:
            self.verificationErrors.append(str(e))
        try:
            self.assertEqual("Parent", sel.get_text(
                "id=id_formset_DM1FamilyMembers-0-ClinicalData____DM1FamilyMembers____DM1Relationship"))
        except AssertionError as e:
            self.verificationErrors.append(str(e))
        try:
            self.assertEqual("DM1", sel.get_text(
                "id=id_formset_DM1FamilyMembers-0-ClinicalData____DM1FamilyMembers____DM1FamilyDiagnosis"))
        except AssertionError as e:
            self.verificationErrors.append(str(e))
        try:
            self.assertEqual("1", sel.get_value(
                "id=id_formset_DM1FamilyMembers-0-ClinicalData____DM1FamilyMembers____DM1FamilyPatientRecord"))
        except AssertionError as e:
            self.verificationErrors.append(str(e))
        try:
            self.assertEqual("Female", sel.get_text(
                "id=id_formset_DM1FamilyMembers-1-ClinicalData____DM1FamilyMembers____DM1Sex"))
        except AssertionError as e:
            self.verificationErrors.append(str(e))
        try:
            self.assertEqual("Sibling", sel.get_text(
                "id=id_formset_DM1FamilyMembers-1-ClinicalData____DM1FamilyMembers____DM1Relationship"))
        except AssertionError as e:
            self.verificationErrors.append(str(e))
        try:
            self.assertEqual("DM2", sel.get_text(
                "id=id_formset_DM1FamilyMembers-1-ClinicalData____DM1FamilyMembers____DM1FamilyDiagnosis"))
        except AssertionError as e:
            self.verificationErrors.append(str(e))
        try:
            self.assertEqual("2", sel.get_value(
                "id=id_formset_DM1FamilyMembers-1-ClinicalData____DM1FamilyMembers____DM1FamilyPatientRecord"))
        except AssertionError as e:
            self.verificationErrors.append(str(e))
        try:
            self.assertEqual("Male", sel.get_text(
                "id=id_formset_DM1FamilyMembers-2-ClinicalData____DM1FamilyMembers____DM1Sex"))
        except AssertionError as e:
            self.verificationErrors.append(str(e))
        try:
            self.assertEqual("Child", sel.get_text(
                "id=id_formset_DM1FamilyMembers-2-ClinicalData____DM1FamilyMembers____DM1Relationship"))
        except AssertionError as e:
            self.verificationErrors.append(str(e))
        try:
            self.assertEqual("Dont know", sel.get_text(
                "id=id_formset_DM1FamilyMembers-2-ClinicalData____DM1FamilyMembers____DM1FamilyDiagnosis"))
        except AssertionError as e:
            self.verificationErrors.append(str(e))
        try:
            self.assertEqual("3", sel.get_value(
                "id=id_formset_DM1FamilyMembers-2-ClinicalData____DM1FamilyMembers____DM1FamilyPatientRecord"))
        except AssertionError as e:
            self.verificationErrors.append(str(e))
        try:
            self.assertEqual("d2", sel.get_value(
                "id=id_formset_DM1ClinicalTrials-0-ClinicalData____DM1ClinicalTrials____DM1DrugName"))
        except AssertionError as e:
            self.verificationErrors.append(str(e))
        try:
            self.assertEqual("t2", sel.get_value(
                "id=id_formset_DM1ClinicalTrials-0-ClinicalData____DM1ClinicalTrials____DM1TrialName"))
        except AssertionError as e:
            self.verificationErrors.append(str(e))
        try:
            self.assertEqual("s2", sel.get_value(
                "id=id_formset_DM1ClinicalTrials-0-ClinicalData____DM1ClinicalTrials____DM1TrialSponsor"))
        except AssertionError as e:
            self.verificationErrors.append(str(e))
        try:
            self.assertEqual("p2", sel.get_value(
                "id=id_formset_DM1ClinicalTrials-0-ClinicalData____DM1ClinicalTrials____DM1TrialPhase"))
        except AssertionError as e:
            self.verificationErrors.append(str(e))
        try:
            self.assertEqual("d3", sel.get_value(
                "id=id_formset_DM1ClinicalTrials-1-ClinicalData____DM1ClinicalTrials____DM1DrugName"))
        except AssertionError as e:
            self.verificationErrors.append(str(e))
        try:
            self.assertEqual("t3", sel.get_value(
                "id=id_formset_DM1ClinicalTrials-1-ClinicalData____DM1ClinicalTrials____DM1TrialName"))
        except AssertionError as e:
            self.verificationErrors.append(str(e))
        try:
            self.assertEqual("s3", sel.get_value(
                "id=id_formset_DM1ClinicalTrials-1-ClinicalData____DM1ClinicalTrials____DM1TrialSponsor"))
        except AssertionError as e:
            self.verificationErrors.append(str(e))
        try:
            self.assertEqual("p3", sel.get_value(
                "id=id_formset_DM1ClinicalTrials-1-ClinicalData____DM1ClinicalTrials____DM1TrialPhase"))
        except AssertionError as e:
            self.verificationErrors.append(str(e))
        try:
            self.assertEqual("r1", sel.get_value(
                "id=id_formset_DM1OtherRegistry-0-ClinicalData____DM1OtherRegistry____DM1OtherRegistry"))
        except AssertionError as e:
            self.verificationErrors.append(str(e))
        try:
            self.assertEqual("r2", sel.get_value(
                "id=id_formset_DM1OtherRegistry-1-ClinicalData____DM1OtherRegistry____DM1OtherRegistry"))
        except AssertionError as e:
            self.verificationErrors.append(str(e))
        try:
            self.assertEqual("r4", sel.get_value(
                "id=id_formset_DM1OtherRegistry-2-ClinicalData____DM1OtherRegistry____DM1OtherRegistry"))
        except AssertionError as e:
            self.verificationErrors.append(str(e))
        try:
            self.assertEqual("r5", sel.get_value(
                "id=id_formset_DM1OtherRegistry-3-ClinicalData____DM1OtherRegistry____DM1OtherRegistry"))
        except AssertionError as e:
            self.verificationErrors.append(str(e))
        try:
            self.assertEqual("r6", sel.get_value(
                "id=id_formset_DM1OtherRegistry-4-ClinicalData____DM1OtherRegistry____DM1OtherRegistry"))
        except AssertionError as e:
            self.verificationErrors.append(str(e))
        try:
            self.assertEqual("yay", sel.get_value("id=id_ClinicalData____DM1Notes____DM1Notes"))
        except AssertionError as e:
            self.verificationErrors.append(str(e))
        sel.click("link=Log out")
