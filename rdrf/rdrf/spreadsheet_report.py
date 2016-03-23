class SpreadSheetReport(object):

    def __init__(self, user, registry_model, working_groups, cdes, time_window=None):
        self.user = user
        self.working_groups = working_groups
        self.registry_model = registry_model
        if time_window is None:
            self.report_type = "current"
        else:
            self.report_type = "longitudinal"

        self.time_window = time_window
        self.cdes = cdes

    def _security_check(self):
        pass

    def generate(self):
        self._security_check()
        workbook = self._create_workbook()
        for cde in cdes:
            sheet = self._create_sheet(cde)

    def _create_workbook(self):
        pass

    def _create_sheet(self, cde):
        sheet = None
        for patient in self._get_patients():
            self._add_row(patient, cde, sheet)
        return sheet

    def _get_patients(self):
        from rdrf.registry.patients import Patient
        return Patient.objects.filter(working_groups__in=[self.working_groups],
                                      rdrf_registry__in=[self.registry_model])
