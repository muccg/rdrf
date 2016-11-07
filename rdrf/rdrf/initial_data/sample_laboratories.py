'''Sample laboratories from AU and NZ...'''
from registry.genetic import models


def load_data(**kwargs):
    for lab in labs:
        lab_defaults = lab.copy()
        name = lab_defaults.pop('name')
        models.Laboratory.objects.get_or_create(name=name, defaults=lab_defaults)


labs = [{
        "name": "Neurogenetics Laboratory, Royal Perth Hospital",
        "contact_phone": "08 9111 2222",
        "contact_name": "Mark Davis",
        "contact_email": "mark.davis@health.wa.gov.au",
        "address": ""
        }, {
        "name": "Diagnostic Genetics, LabPlus",
        "contact_phone": "",
        "contact_name": "Donald Love",
        "contact_email": "",
        "address": "PO Box 110031\r\nAuckland City Hospital\r\nAuckland 1148"
        }, {
        "name": "Genetics and Molecular Pathology, SA Pathology (Women\\u2019s and Children\\u2019s Hospital) ",
        "contact_phone": "08 8111 2222",
        "contact_name": "Kathie Friend",
        "contact_email": "kathryn.friend@adelaide.edu.au",
        "address": ""
        }, {
        "name": "Molecular Genetics Laboratory, Pathology Queensland",
        "contact_phone": "07",
        "contact_name": "Val Hyland",
        "contact_email": "Val_Hyland@health.qld.gov.au",
        "address": ""
        }, {
        "name": "Molecular Medicine Laboratory, Concord Repatriation General Hospital",
        "contact_phone": "02 912121001",
        "contact_name": "Danqing Zhu",
        "contact_email": "molmed@med.usyd.edu.au",
        "address": ""
        }, {
        "name": "VCGS Molecular Genetics Laboratory, Murdoch Childrens research Institute",
        "contact_phone": "",
        "contact_name": "Desir\\u00e9e du Sart",
        "contact_email": "dusart.desiree@mcri.edu.au",
        "address": ""
        }, {
        "name": "Victorian Clinical Genetics Service",
        "contact_phone": "8343 1777",
        "contact_name": "",
        "contact_email": "",
        "address": "Flemington Road, Parkville"
        }]
