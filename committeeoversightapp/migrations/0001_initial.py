# Generated by Django 2.1.2 on 2018-11-07 17:12

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        ('legislative', '0008_longer_event_name'),
    ]

    operations = [
        migrations.CreateModel(
            name='HearingCategory',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
            ],
        ),
        migrations.CreateModel(
            name='HearingCategoryType',
            fields=[
                ('id', models.CharField(max_length=100, primary_key=True, serialize=False)),
                ('name', models.CharField(max_length=100)),
            ],
        ),
        migrations.CreateModel(
            name='WitnessDetails',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('organization', models.CharField(blank=True, max_length=100, null=True)),
                ('document', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, to='legislative.EventDocument')),
                ('witness', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='legislative.EventParticipant')),
            ],
        ),
        migrations.AddField(
            model_name='hearingcategory',
            name='category',
            field=models.ForeignKey(null=True, on_delete=django.db.models.deletion.CASCADE, to='committeeoversightapp.HearingCategoryType'),
        ),
        migrations.AddField(
            model_name='hearingcategory',
            name='event',
            field=models.ForeignKey(null=True, on_delete=django.db.models.deletion.CASCADE, to='legislative.Event'),
        ),
    ]
