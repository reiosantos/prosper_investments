# Generated by Django 2.2.3 on 2019-10-31 09:29

from django.db import migrations


class Migration(migrations.Migration):
	dependencies = [
		('user', '0002_auto_20191025_0912'),
	]

	operations = [
		migrations.DeleteModel(
			name='ApiKey',
		),
	]
