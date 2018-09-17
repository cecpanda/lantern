# Generated by Django 2.0.6 on 2018-08-01 02:46

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('tft', '0010_auto_20180801_1028'),
    ]

    operations = [
        migrations.AlterField(
            model_name='order',
            name='charge_group',
            field=models.ForeignKey(default=None, on_delete=django.db.models.deletion.PROTECT, related_name='chargeorders', to='auth.Group', verbose_name='责任工程'),
            preserve_default=False,
        ),
    ]
