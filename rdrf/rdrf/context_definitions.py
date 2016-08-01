GRID_PATIENT_LISTING = [
     {
        "access": {
            "default": False,
            "permission": "patients.can_see_full_name"
        },
        "data": "full_name",
        "label": "Patient",
        "model": "Patient",
        "order": 0
    },
    {
        "access": {
            "default": False,
            "permission": "patients.can_see_dob",
        },
        "data": "date_of_birth",
        "label": "Date of Birth",
        "model": "Patient",
        "order": 1
    },

    {
        "access": {
            "default": False,
            "permission": "patients.can_see_working_groups"
        },
        "data": "working_groups_display",
        "label": "Working Groups",
        "model": "Patient",
        "order": 2
    }, {
        "access": {
            "default": False,
            "permission": "patients.can_see_diagnosis_progress"
        },
        "data": "diagnosis_progress",
        "label": "Diagnosis Entry Progress",
        "model": "Patient",
        "order": 3
    }, {
        "access": {
            "default": False,
            "permission": "patients.can_see_diagnosis_currency"
        },
        "data": "diagnosis_currency",
        "label": "Updated < 365 days",
        "model": "Patient",
        "order": 4
    }, {
        "access": {
            "default": False,
            "permission": "patients.can_see_genetic_data_map"
        },
        "data": "genetic_data_map",
        "label": "Genetic Data",
        "model": "Patient",
        "order": 5
    },
     {
        "access": {
            "default": False,
            "permission": "patients.can_see_data_modules",
        },
        "data": "context_menu",
        "label": "Modules",
        "model": "func",
        "order": 6
    }
]
