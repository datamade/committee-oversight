# Generated by Django 2.1.15 on 2020-01-15 23:04

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('legislative', '0008_longer_event_name'),
        ('committeeoversightapp', '0021_auto_20191125_1256'),
    ]

    operations = [
        migrations.CreateModel(
            name='HearingEvent',
            fields=[
            ],
            options={
                'proxy': True,
                'indexes': [],
            },
            bases=('legislative.event',),
        ),
    ]
