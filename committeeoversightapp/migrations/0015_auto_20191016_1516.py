# Generated by Django 2.1.13 on 2019-10-16 20:16

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('committeeoversightapp', '0014_auto_20191009_1528'),
    ]

    operations = [
        migrations.AddField(
            model_name='committeedetailpage',
            name='chair',
            field=models.TextField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name='committeedetailpage',
            name='hide_rating',
            field=models.BooleanField(default=False),
        ),
    ]
