# Generated by Django 2.2.16 on 2020-09-09 13:02

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("addons", "0019_auto_20200901_1459"),
    ]

    operations = [
        migrations.AlterField(
            model_name="addon",
            name="total_downloads",
            field=models.PositiveIntegerField(
                db_column="totaldownloads", default=0, null=True
            ),
        ),
    ]
