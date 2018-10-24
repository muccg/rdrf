'''Sample laboratories from AU and NZ...'''
from registry.genetic import models


def load_data(**kwargs):
    for lab in labs:
        lab_defaults = lab.copy()
        name = lab_defaults.pop('name')
        models.Laboratory.objects.get_or_create(name=name, defaults=lab_defaults)


labs = [{"name": "Neurogenetics Laboratory, Royal Perth Hospital",
         "contact_phone": "sfsdfs",
         "contact_name": "Fred Bloggs",
         "contact_email": "test@example.com",
         "address": ""}]
