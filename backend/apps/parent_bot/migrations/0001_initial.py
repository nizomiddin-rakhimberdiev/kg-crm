"""
Parent bot contact index (ADR-27): HMAC digests that tell the bot which
organizations know a phone or a chat. Metadata plane: own organization or
platform mode, never another tenant. `check_rls` 50 -> 51.
"""

import django.db.models.deletion
import uuid
from django.db import migrations, models

from apps.core.db import attach_tenant_guards
from apps.core.rls import metadata_policy_sql_for, teardown_sql_for


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        ('organizations', '0002_organization_logo'),
    ]

    operations = [
        migrations.CreateModel(
            name='ContactIndex',
            fields=[
                ('id', models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ('created_at', models.DateTimeField(auto_now_add=True, db_index=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('is_active', models.BooleanField(db_index=True, default=True)),
                ('kind', models.CharField(choices=[('phone', 'Phone'), ('chat', 'Telegram chat')], max_length=5)),
                ('digest', models.CharField(max_length=64)),
                ('organization', models.ForeignKey(editable=False, on_delete=django.db.models.deletion.RESTRICT, related_name='%(app_label)s_%(class)s_set', to='organizations.organization')),
            ],
            options={
                'db_table': 'contact_index',
                'indexes': [models.Index(fields=['kind', 'digest'], name='ix_contact_index_lookup')],
                'constraints': [models.UniqueConstraint(fields=('kind', 'digest', 'organization'), name='uq_contact_index_entry'), models.CheckConstraint(condition=models.Q(('kind__in', ['phone', 'chat'])), name='ck_contact_index_kind')],
            },
        ),
        *attach_tenant_guards("contact_index"),
        migrations.RunSQL(
            sql=metadata_policy_sql_for("contact_index"),
            reverse_sql=teardown_sql_for("contact_index"),
        ),
    ]
