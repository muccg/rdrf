# -*- coding: utf-8 -*-


from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('auth', '0006_require_contenttypes_0002'),
    ]

    operations = [
        migrations.CreateModel(
            name='Query',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('title', models.CharField(max_length=255)),
                ('description', models.TextField(null=True, blank=True)),
                ('mongo_search_type', models.CharField(default='F', max_length=1,
                                                       choices=[('F', 'Find'), ('A', 'Aggregation')])),
                ('collection', models.CharField(default='cdes', max_length=255)),
                ('criteria', models.TextField(null=True, blank=True)),
                ('projection', models.TextField(null=True, blank=True)),
                ('aggregation', models.TextField(null=True, blank=True)),
                ('sql_query', models.TextField()),
                ('created_by', models.CharField(max_length=255, null=True, blank=True)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('access_group', models.ManyToManyField(to='auth.Group')),
            ],
            options={
                'ordering': ['title'],
                'verbose_name_plural': 'Queries',
            },
        ),
    ]
