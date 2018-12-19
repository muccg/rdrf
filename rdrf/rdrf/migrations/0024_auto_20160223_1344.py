# -*- coding: utf-8 -*-


from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('rdrf', '0023_rdrfcontext_context_form_group'),
    ]

    operations = [
        migrations.AddField(
            model_name='contextformgroup',
            name='naming_scheme',
            field=models.CharField(default='D', max_length=1, choices=[(
                'D', 'Automatic - Date'), ('N', 'Automatic - Number'), ('M', 'Manual - Free Text')]),
        ),
        migrations.AlterField(
            model_name='contextformgroup',
            name='registry',
            field=models.ForeignKey(related_name='context_form_groups', 
                                    to='rdrf.Registry',
                                    on_delete=models.CASCADE),
        ),
        migrations.AlterField(
            model_name='contextformgroupitem',
            name='context_form_group',
            field=models.ForeignKey(related_name='items',
                                    to='rdrf.ContextFormGroup',
                                    on_delete=models.CASCADE),
        ),
        migrations.AlterUniqueTogether(
            name='cdepermittedvalue',
            unique_together=set([('pv_group', 'code')]),
        ),
    ]
