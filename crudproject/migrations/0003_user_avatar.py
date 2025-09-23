# Generated manually for avatar field addition

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("crudproject", "0002_alter_user_options_user_updated_at"),
    ]

    operations = [
        migrations.AddField(
            model_name="user",
            name="avatar",
            field=models.ImageField(blank=True, null=True, upload_to="avatars/"),
        ),
    ]
