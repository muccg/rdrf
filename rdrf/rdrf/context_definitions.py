

GRID_PATIENT_LISTING = [
    {
        "access": {
            "default": True,
            "permission": ""
        },
        "data": "full_name",
        "label": "Patient",
        "order": 1
    }, {
        "access": {
            "default": True,
            "permission": ""
        },
        "data": "date_of_birth",
        "label": "Date of Birth",
        "order": 2
    }, {
        "access": {
            "default": False,
            "permission": "patients.can_see_working_groups"
        },
        "data": "working_groups_display",
        "label": "Working Groups",
        "order": 3
    }, {
        "access": {
            "default": False,
            "permission": "patients.can_see_diagnosis_progress"
        },
        "data": "diagnosis_progress",
        "label": "Diagnosis Entry Progress",
        "order": 4
    }, {
        "access": {
            "default": False,
            "permission": "patients.can_see_diagnosis_currency"
        },
        "data": "diagnosis_currency",
        "label": "Updated < 365 days",
        "order": 5
    }, {
        "access": {
            "default": False,
            "permission": "patients.can_see_genetic_data_map"
        },
        "data": "genetic_data_map",
        "label": "Genetic Data",
        "order": 6
    }, {
        "access": {
            "default": True,
            "permission": ""
        },
        "data": "data_modules",
        "label": "Modules",
        "order": 7
    },
    {
        "access": {
            "default": True,
            "permission": ""
        },
        "data": "diagnosis_progress",
        "label": "Data Entry Progress",
        "order": 8
    }
]


GRID_CONTEXT_LISTING = [
     {
        "access": {
            "default": True,
            "permission": "patients.can_see_full_name"
        },
        "data": "patient_link",
        "label": "Patient",
        "model": "func",
        "order": 0
    },
    {
        "access": {
            "default": True,
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
            "permission": ""
        },
        "data": "created_at",
        "label": "Created",
        "model": "RDRFContext",
        "order": 2
    },

    {
        "access": {
            "default": False,
            "permission": "patients.can_see_working_groups"
        },
        "data": "working_groups_display",
        "label": "Working Groups",
        "model": "Patient",
        "order": 3
    }, {
        "access": {
            "default": False,
            "permission": "patients.can_see_diagnosis_progress"
        },
        "data": "diagnosis_progress",
        "label": "Diagnosis Entry Progress",
        "model": "Patient",
        "order": 4
    }, {
        "access": {
            "default": False,
            "permission": "patients.can_see_diagnosis_currency"
        },
        "data": "diagnosis_currency",
        "label": "Updated < 365 days",
        "model": "Patient",
        "order": 5
    }, {
        "access": {
            "default": False,
            "permission": "patients.can_see_genetic_data_map"
        },
        "data": "genetic_data_map",
        "label": "Genetic Data",
        "model": "Patient",
        "order": 6
    },
     {
        "access": {
            "default": False,
            "permission": "patients.can_see_data_modules",
        },
        "data": "context_menu",
        "label": "Modules",
        "model": "func",
        "order": 9
    }
]
