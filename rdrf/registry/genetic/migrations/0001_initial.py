# -*- coding: utf-8 -*-


from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
    ]

    operations = [
        migrations.CreateModel(
            name='Gene',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('symbol', models.TextField()),
                ('hgnc_id', models.TextField(verbose_name='HGNC ID')),
                ('name', models.TextField()),
                ('status', models.TextField()),
                ('chromosome', models.TextField()),
                ('accession_numbers', models.TextField()),
                ('refseq_id', models.TextField(verbose_name='RefSeq ID')),
            ],
            options={
                'ordering': ['symbol'],
            },
        ),
        migrations.CreateModel(
            name='Laboratory',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('name', models.CharField(max_length=256)),
                ('address', models.TextField(max_length=200, blank=True)),
                ('contact_name', models.CharField(max_length=200, blank=True)),
                ('contact_email', models.EmailField(max_length=254, blank=True)),
                ('contact_phone', models.CharField(max_length=50, blank=True)),
            ],
            options={
                'verbose_name_plural': 'laboratories',
            },
        ),
        migrations.CreateModel(
            name='Technique',
            fields=[
                ('name', models.CharField(max_length=50, serialize=False, primary_key=True)),
            ],
        ),
    ]
