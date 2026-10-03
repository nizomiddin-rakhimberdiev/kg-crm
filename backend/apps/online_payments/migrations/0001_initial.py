"""
Online payments (PLAN 6.1, ADR-26): merchant keys, payment links and
provider transactions — all three tenant tables with the same guards as
every other: immutable `organization_id` and a FORCEd RLS policy
(invariant 8). `check_rls` 47 → 50.
"""

import django.db.models.deletion
import uuid
from django.conf import settings
from django.db import migrations, models

from apps.core.rls import policy_sql_for, teardown_sql_for
from apps.core.db import attach_tenant_guards


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        ('branches', '0002_branch_tenancy_guard'),
        ('finance', '0010_alter_childledgerentry_entry_type_and_more'),
        ('organizations', '0002_organization_logo'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name='PaymentLink',
            fields=[
                ('id', models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ('created_at', models.DateTimeField(auto_now_add=True, db_index=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('is_active', models.BooleanField(db_index=True, default=True)),
                ('token', models.CharField(editable=False, max_length=64, unique=True)),
                ('expires_at', models.DateTimeField()),
                ('branch', models.ForeignKey(on_delete=django.db.models.deletion.RESTRICT, related_name='%(app_label)s_%(class)s_set', to='branches.branch')),
                ('created_by', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='+', to=settings.AUTH_USER_MODEL)),
                ('invoice', models.ForeignKey(on_delete=django.db.models.deletion.RESTRICT, related_name='payment_links', to='finance.invoice')),
                ('organization', models.ForeignKey(editable=False, on_delete=django.db.models.deletion.RESTRICT, related_name='%(app_label)s_%(class)s_set', to='organizations.organization')),
            ],
            options={
                'db_table': 'payment_link',
                'ordering': ['-created_at'],
            },
        ),
        migrations.CreateModel(
            name='MerchantCredential',
            fields=[
                ('id', models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ('created_at', models.DateTimeField(auto_now_add=True, db_index=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('is_active', models.BooleanField(db_index=True, default=True)),
                ('provider', models.CharField(choices=[('payme', 'Payme'), ('click', 'Click')], max_length=10)),
                ('merchant_id', models.CharField(max_length=64)),
                ('service_id', models.CharField(blank=True, max_length=32)),
                ('secret_encrypted', models.TextField(editable=False)),
                ('secret_hint', models.CharField(blank=True, editable=False, max_length=4)),
                ('sandbox', models.BooleanField(default=False)),
                ('organization', models.ForeignKey(editable=False, on_delete=django.db.models.deletion.RESTRICT, related_name='%(app_label)s_%(class)s_set', to='organizations.organization')),
            ],
            options={
                'db_table': 'merchant_credential',
                'constraints': [models.UniqueConstraint(condition=models.Q(('is_active', True)), fields=('organization', 'provider'), name='uq_merchant_credential_active')],
            },
        ),
        migrations.CreateModel(
            name='OnlineTransaction',
            fields=[
                ('id', models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ('created_at', models.DateTimeField(auto_now_add=True, db_index=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('is_active', models.BooleanField(db_index=True, default=True)),
                ('provider', models.CharField(choices=[('payme', 'Payme'), ('click', 'Click')], max_length=10)),
                ('provider_txn_id', models.CharField(max_length=64)),
                ('amount', models.DecimalField(decimal_places=2, max_digits=12)),
                ('state', models.SmallIntegerField(choices=[(1, 'Yaratildi'), (2, 'Toʻlandi'), (-1, 'Bekor qilindi'), (-2, 'Qaytarildi')], default=1)),
                ('reason', models.SmallIntegerField(blank=True, null=True)),
                ('provider_time', models.BigIntegerField(blank=True, null=True)),
                ('performed_at', models.DateTimeField(blank=True, null=True)),
                ('cancelled_at', models.DateTimeField(blank=True, null=True)),
                ('branch', models.ForeignKey(on_delete=django.db.models.deletion.RESTRICT, related_name='%(app_label)s_%(class)s_set', to='branches.branch')),
                ('invoice', models.ForeignKey(on_delete=django.db.models.deletion.RESTRICT, related_name='online_transactions', to='finance.invoice')),
                ('organization', models.ForeignKey(editable=False, on_delete=django.db.models.deletion.RESTRICT, related_name='%(app_label)s_%(class)s_set', to='organizations.organization')),
                ('payment', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.RESTRICT, related_name='online_transactions', to='finance.payment')),
            ],
            options={
                'db_table': 'online_transaction',
                'ordering': ['-created_at'],
                'constraints': [models.UniqueConstraint(fields=('provider', 'provider_txn_id'), name='uq_online_txn_provider_id'), models.CheckConstraint(condition=models.Q(('amount__gt', 0)), name='ck_online_txn_amount')],
            },
        ),
        *attach_tenant_guards("payment_link"),
        migrations.RunSQL(sql=policy_sql_for("payment_link"), reverse_sql=teardown_sql_for("payment_link")),
        *attach_tenant_guards("merchant_credential"),
        migrations.RunSQL(sql=policy_sql_for("merchant_credential"), reverse_sql=teardown_sql_for("merchant_credential")),
        *attach_tenant_guards("online_transaction"),
        migrations.RunSQL(sql=policy_sql_for("online_transaction"), reverse_sql=teardown_sql_for("online_transaction")),
    ]
