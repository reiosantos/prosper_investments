# Generated by Django 2.2.3 on 2019-12-11 17:54

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('user', '0003_delete_apikey'),
        ('permission', '0002_contributionstatus_created_by'),
    ]

    operations = [
        migrations.RenameModel(
            old_name='ContributionPermission',
            new_name='VenuePermission',
        ),
        migrations.DeleteModel(
            name='ContributionStatus',
        ),
    ]