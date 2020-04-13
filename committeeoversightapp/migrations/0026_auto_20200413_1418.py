# Generated by Django 2.1.15 on 2020-04-13 19:18

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('committeeoversightapp', '0025_congress_inactive_days'),
    ]

    operations = [
        migrations.AlterField(
            model_name='congress',
            name='inactive_days',
            field=models.IntegerField(default=62, help_text="The default value here reflects the Lugar Center's determination that an average Congress does not hold hearings for about 2 months of its duration. Setting this value higher means that a Congress's scores will be calculated relative to a shorter length."),
        ),
    ]
