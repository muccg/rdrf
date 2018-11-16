from rdrf.models.workflow_models import ClinicianSignupRequest

class RegistrationWorkflow:
    def __init__(self, token, request_object):
        self.token = token
        self.request_object = request_object

    def get_template(self):
        pass


class ClinicianSignupWorkflow(RegistrationWorkflow):
    def get_template(self):
        return "registration/clinician_registration.html"

def get_registration_workflow(token):
    try:
        csr = ClinicianSignupRequest.objects.get(token=token,
                                                 state="emailed")
        return ClinicianSignupWorkflow(token, csr)
    except ClinicianSignupRequest.DoesNotExist:
        pass
