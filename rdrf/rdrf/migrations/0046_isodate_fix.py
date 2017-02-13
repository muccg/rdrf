# -*- coding: utf-8 -*-
from __future__ import unicode_literals
from django.db import migrations, models

from rdrf.models import Modjgo, CommonDataElement


from copy import deepcopy

def is_date(cde_dict):
    code = cde_dict["code"]
    try:
        cde_model = CommonDataElement.objects.get(code=code)
        return cde_model.datatype == "date"
    except CommonDataElement.DoesNotExist:
        pass

def munge_datestring(datestring):
    if "T" in datestring:
        t_index = datestring.index("T")
        return datestring[:t_index]
    else:
        return datestring
    

def update_cde(cde):
    old_datestring = cde["value"]
    new_datestring = munge_datestring(old_datestring)
    cde["value"] = new_datestring
        
class TimeStripper:
    data = {}

    @staticmethod
    def forward(klass, apps, schema_editor):
        for m in Modjgo.objects.filter(collection="cdes"):
            if m.data:
                backup_data = deepcopy(m.data)
                TimeStripper.data[m.pk] = backup_data
                if "forms" in m.data:
                    for form in m.data["forms"]:
                        if "sections" in form:
                            for section in form["sections"]:
                                if not section["allow_mutiple"]:
                                    if "cdes" in section:
                                        for cde in section["cdes"]:
                                            if is_date(cde):
                                                update_cde(cde)
                                else:
                                    items = section["cdes"]
                                    for item in items:
                                        for cde in item:
                                            if is_date[cde]:
                                                update_cde(cde)


    
                                                

                                                
                        
                


    @staticmethod
    def backwards(klass, apps, schema_editor):
        for m in Modjgo.objects.filter(collection="cdes"):
            if m.pk in TimeStripper.data:
                m.data = TimeStripper.data[m.pk]
                m.save()
                
        
        
        
    

def set_fks(apps, schema_editor):
    from rdrf.models import Registry, RegistryForm, Section, CommonDataElement
    
    m = lambda model: apps.get_model("rdrf", model)
    CDEFile = m("CDEFile")
    for f in CDEFile.objects.all():
        try:
            f.registry = m("Registry").objects.get(code=f.registry_code)
        except Registry.DoesNotExist:
            msg = "Cannot set registry back on CDEFile %s registry_code = %s" % (f.pk, f.registry_code)
            print(msg)

        try:
            f.form = m("RegistryForm").objects.get(name=f.form_name,
                                               registry=f.registry)
        except RegistryForm.DoesNotExist:
            msg = "Cannot set form back on CDEFile %s name = %s" % (f.pk,
                                                                    f.form_name)
            print(msg)
            

        try:
            f.section = m("Section").objects.get(code=f.section_code)
        except Section.DoesNotExist:
            msg = "Cannot set section back on CDEFile %s code = %s" % (f.pk,
                                                                       f.section_code)
            print(msg)

        try:
            f.cde = m("CommonDataElement").objects.get(code=f.cde_code)
        except CommonDataElement.DoesNotExist:
            msg = "Cannot set cde back on CDEFile %s code = %s" % (f.pk,
                                                                   f.cde_code)

            print(msg)

        try:
            f.save()
        except Exception as ex:
            print("could not revert CDEFile %s back: %s" % (f.pk,
                                                            ex))

       
class Migration(migrations.Migration):

    dependencies = [
        ('rdrf', '0045_remove_old_cdefile_fields'),
    ]

    operations = [
        migrations.RunPython(stripoff_time, putback_time)
        
       
    ]
