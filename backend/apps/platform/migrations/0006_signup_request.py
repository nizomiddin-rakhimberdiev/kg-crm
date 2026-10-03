"""
Self-signup requests (PLAN 6.7, ADR-28). Platform plane like `platform_lead`:
no tenant exists yet when the row is written.
"""

import django.db.models.deletion
import uuid
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('organizations', '0002_organization_logo'),
        ('platform_console', '0005_platformuser_totp_backup_codes'),
    ]

    operations = [
        migrations.CreateModel(
            name='SignupRequest',
            fields=[
                ('id', models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ('created_at', models.DateTimeField(auto_now_add=True, db_index=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('email', models.EmailField(db_index=True, max_length=254)),
                ('full_name', models.CharField(max_length=150)),
                ('kindergarten_name', models.CharField(max_length=200)),
                ('phone', models.CharField(max_length=13)),
                ('language', models.CharField(default='uz', max_length=2)),
                ('token_hash', models.CharField(max_length=64, unique=True)),
                ('expires_at', models.DateTimeField()),
                ('confirmed_at', models.DateTimeField(blank=True, null=True)),
                ('organization', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.RESTRICT, related_name='signup_requests', to='organizations.organization')),
            ],
            options={
                'db_table': 'platform_signup_request',
                'ordering': ['-created_at'],
            },
        ),
    ]
