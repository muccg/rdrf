# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations


def set_codes(apps, schema_editor):
    CDEFile = apps.get_model("rdrf", "CDEFile")

    for f in CDEFile.objects.all():
        if f.registry:
            f.registry_code = f.registry.code
        else:
            print("CDEFile %s has null registry" % f.pk)
        if f.form:
            f.form_name = f.form.name
        else:
            print("CDEFile %s has null form" % f.pk)
        if f.section:
            f.section_code = f.section.code
        else:
            print("CDEFile %s has null section" % f.pk)
        if f.cde:
            f.cde_code = f.cde.code
        else:
            print("CDEFile %s has null cde" % f.pk)

        try:
            f.save()
        except Exception as ex:
            print("Could not set codes on CDEFile %s: %s" % (f.pk,
                                                             ex))


def set_fks(apps, schema_editor):
    from rdrf.models.definition.models import Registry, RegistryForm, Section, CommonDataElement

    def m(model): return apps.get_model("rdrf", model)
    CDEFile = m("CDEFile")
    for f in CDEFile.objects.all():
        try:
            f.registry = m("Registry").objects.get(code=f.registry_code)
        except Registry.DoesNotExist:
            msg = "Cannot set registry back on CDEFile %s registry_code = %s" % (
                f.pk, f.registry_code)
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
        ('rdrf', '0043_auto_20170131_1517'),
    ]

    operations = [
        migrations.RunPython(set_codes, set_fks)


    ]
