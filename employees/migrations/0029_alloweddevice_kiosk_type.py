# Generated manually to add AllowedDevice.kiosk_type

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('employees', '0028_admin_groups_gridfsfile_profile_user'),
    ]

    operations = [
        migrations.AddField(
            model_name='alloweddevice',
            name='kiosk_type',
            field=models.CharField(
                choices=[('attendance', 'Attendance Kiosk'), ('canteen', 'Canteen Kiosk')],
                default='attendance',
                max_length=20,
            ),
        ),
    ]
