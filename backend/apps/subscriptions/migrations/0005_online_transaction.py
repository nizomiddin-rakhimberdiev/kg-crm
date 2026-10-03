"""
Subscription invoices paid through Radix's own Payme / Click merchant
(PLAN 6.4): the `online` payment method and the provider transaction
table. Metadata plane, like every subscription table. `check_rls` 51 -> 52.
"""

import django.db.models.deletion
import uuid
from decimal import Decimal
from django.db import migrations, models

from apps.core.db import attach_tenant_guards
from apps.core.rls import metadata_policy_sql_for, teardown_sql_for


class Migration(migrations.Migration):

    dependencies = [
        ('organizations', '0002_organization_logo'),
        ('subscriptions', '0004_alter_subscription_status_and_more'),
    ]

    operations = [
        migrations.AlterField(
            model_name='subscriptionpayment',
            name='method',
            field=models.CharField(choices=[('bank_transfer', 'Bank oʻtkazmasi'), ('card', 'Karta'), ('cash', 'Naqd'), ('online', 'Payme / Click')], default='bank_transfer', max_length=20),
        ),
        migrations.CreateModel(
            name='SubscriptionOnlineTransaction',
            fields=[
                ('id', models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ('created_at', models.DateTimeField(auto_now_add=True, db_index=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('is_active', models.BooleanField(db_index=True, default=True)),
                ('provider', models.CharField(max_length=10)),
                ('provider_txn_id', models.CharField(max_length=64)),
                ('amount', models.DecimalField(decimal_places=2, max_digits=12)),
                ('state', models.SmallIntegerField(default=1)),
                ('reason', models.SmallIntegerField(blank=True, null=True)),
                ('provider_time', models.BigIntegerField(blank=True, null=True)),
                ('performed_at', models.DateTimeField(blank=True, null=True)),
                ('cancelled_at', models.DateTimeField(blank=True, null=True)),
                ('organization', models.ForeignKey(editable=False, on_delete=django.db.models.deletion.RESTRICT, related_name='%(app_label)s_%(class)s_set', to='organizations.organization')),
                ('payment', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.RESTRICT, related_name='online_transactions', to='subscriptions.subscriptionpayment')),
                ('subscription_invoice', models.ForeignKey(on_delete=django.db.models.deletion.RESTRICT, related_name='online_transactions', to='subscriptions.subscriptioninvoice')),
            ],
            options={
                'db_table': 'subscription_online_transaction',
                'ordering': ['-created_at'],
                'constraints': [models.UniqueConstraint(fields=('provider', 'provider_txn_id'), name='uq_sub_online_txn_provider_id'), models.CheckConstraint(condition=models.Q(('amount__gt', Decimal('0'))), name='ck_sub_online_txn_amount'), models.CheckConstraint(condition=models.Q(('provider__in', ['payme', 'click'])), name='ck_sub_online_txn_provider')],
            },
        ),
        migrations.AddConstraint(
            model_name='subscriptionpayment',
            constraint=models.CheckConstraint(condition=models.Q(('method__in', ['bank_transfer', 'card', 'cash', 'online'])), name='ck_sub_payment_method'),
        ),
        *attach_tenant_guards("subscription_online_transaction"),
        migrations.RunSQL(
            sql=metadata_policy_sql_for("subscription_online_transaction"),
            reverse_sql=teardown_sql_for("subscription_online_transaction"),
        ),
    ]
