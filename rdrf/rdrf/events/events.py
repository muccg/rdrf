class EventType:
    OTHER_CLINICIAN = "other-clinician"
    NEW_PATIENT = "new-patient"
    NEW_PATIENT_PARENT = "new-patient-parent"
    ACCOUNT_LOCKED = "account-locked"
    ACCOUNT_VERIFIED = "account-verified"
    PASSWORD_EXPIRY_WARNING = "password-expiry-warning"
    REMINDER = "reminder"
    CLINICIAN_SELECTED = "clinician-selected" # existing clinician selected by patient as their clinician

    @classmethod
    def is_registration(cls, evt):
        return evt in (cls.NEW_PATIENT, cls.NEW_PATIENT_PARENT)
