# Generated by Django 2.1.15 on 2020-04-03 22:04

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('committeeoversightapp', '0022_hearingevent'),
    ]

    operations = [
        migrations.AddField(
            model_name='committeedetailpage',
            name='display_name',
            field=models.TextField(blank=True, null=True),
        ),
    ]
