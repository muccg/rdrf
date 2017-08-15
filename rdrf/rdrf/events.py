class EventType:
    OTHER_CLINICIAN = "other-clinician"
    NEW_PATIENT = "new-patient"
    NEW_PATIENT_PARENT = "new-patient-parent"
    ACCOUNT_LOCKED = "account-locked"
    ACCOUNT_VERIFIED = "account-verified"
    REMINDER = "reminder"

    @classmethod
    def is_registration(cls, evt):
        return evt in (cls.NEW_PATIENT, cls.NEW_PATIENT_PARENT)
