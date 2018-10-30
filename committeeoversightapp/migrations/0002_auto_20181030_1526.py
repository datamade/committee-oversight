# Generated by Django 2.1.2 on 2018-10-30 20:26

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('committeeoversightapp', '0001_initial'),
    ]

    operations = [
        migrations.AlterField(
            model_name='witnessdetails',
            name='document',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, to='legislative.EventDocument'),
        ),
        migrations.AlterField(
            model_name='witnessdetails',
            name='organization',
            field=models.CharField(blank=True, max_length=100, null=True),
        ),
    ]
