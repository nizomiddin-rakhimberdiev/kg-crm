"""
Chiqim qatorlari (PLAN 7.5): nima, qancha, qanchadan.

Tenant jadvali — odatdagi qo'riqchilar va RLS siyosati bilan
(`check_rls` 58 -> 59).
"""

import django.db.models.deletion
import uuid
from decimal import Decimal
from django.db import migrations, models

from apps.core.db import attach_tenant_guards
from apps.core.rls import policy_sql_for, teardown_sql_for


class Migration(migrations.Migration):

    dependencies = [
        ('branches', '0002_branch_tenancy_guard'),
        ('expenses', '0004_alter_expense_status'),
        ('organizations', '0002_organization_logo'),
    ]

    operations = [
        migrations.CreateModel(
            name='ExpenseItem',
            fields=[
                ('id', models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ('created_at', models.DateTimeField(auto_now_add=True, db_index=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('is_active', models.BooleanField(db_index=True, default=True)),
                ('name', models.CharField(max_length=120)),
                ('quantity', models.DecimalField(decimal_places=3, max_digits=12)),
                ('unit', models.CharField(default='dona', max_length=10)),
                ('unit_price', models.DecimalField(decimal_places=2, max_digits=12)),
                ('line_total', models.DecimalField(decimal_places=2, max_digits=12)),
                ('note', models.CharField(blank=True, max_length=255)),
                ('branch', models.ForeignKey(on_delete=django.db.models.deletion.RESTRICT, related_name='%(app_label)s_%(class)s_set', to='branches.branch')),
                ('expense', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='items', to='expenses.expense')),
                ('organization', models.ForeignKey(editable=False, on_delete=django.db.models.deletion.RESTRICT, related_name='%(app_label)s_%(class)s_set', to='organizations.organization')),
            ],
            options={
                'db_table': 'expense_item',
                'ordering': ['created_at'],
                'constraints': [models.CheckConstraint(condition=models.Q(('quantity__gt', Decimal('0'))), name='ck_expense_item_quantity'), models.CheckConstraint(condition=models.Q(('unit_price__gte', Decimal('0'))), name='ck_expense_item_price'), models.CheckConstraint(condition=models.Q(('line_total__gte', Decimal('0'))), name='ck_expense_item_total')],
            },
        ),
        *attach_tenant_guards("expense_item"),
        migrations.RunSQL(
            sql=policy_sql_for("expense_item"), reverse_sql=teardown_sql_for("expense_item")
        ),
    ]
