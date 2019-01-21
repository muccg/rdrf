# -*- coding: utf-8 -*-


from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('rdrf', '0022_merge'),
    ]

    operations = [
        migrations.AddField(
            model_name='rdrfcontext',
            name='context_form_group',
            field=models.ForeignKey(blank=True,
                                    to='rdrf.ContextFormGroup',
                                    null=True,
                                    on_delete=models.SET_NULL),
        ),
    ]
