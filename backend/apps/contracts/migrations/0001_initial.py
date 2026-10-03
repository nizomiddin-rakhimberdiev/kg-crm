"""
Contract templates and contracts (PLAN 6.5). Both tenant tables carry the
standard guards and RLS policy (`check_rls` 52 -> 54). A contract's frozen
columns — the text and values it was made with — cannot be updated: the
database refuses it (`trg_contract_frozen`), as it refuses a ledger edit.
"""

import django.db.models.deletion
import uuid
from django.conf import settings
from django.db import migrations, models

from apps.core.db import attach_tenant_guards
from apps.core.rls import policy_sql_for, teardown_sql_for

FROZEN_SQL = """
CREATE OR REPLACE FUNCTION kg_guard_contract_frozen() RETURNS trigger AS $$
BEGIN
    IF NEW.rendered_text IS DISTINCT FROM OLD.rendered_text
       OR NEW."values" IS DISTINCT FROM OLD."values"
       OR NEW.number IS DISTINCT FROM OLD.number
       OR NEW.child_id IS DISTINCT FROM OLD.child_id
       OR NEW.guardian_id IS DISTINCT FROM OLD.guardian_id
       OR NEW.template_id IS DISTINCT FROM OLD.template_id
       OR NEW.template_version IS DISTINCT FROM OLD.template_version THEN
        RAISE EXCEPTION 'contract % is frozen: make a new contract instead', OLD.number
            USING ERRCODE = 'check_violation';
    END IF;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trg_contract_frozen BEFORE UPDATE ON contract
    FOR EACH ROW EXECUTE FUNCTION kg_guard_contract_frozen();
"""

FROZEN_REVERSE = """
DROP TRIGGER IF EXISTS trg_contract_frozen ON contract;
DROP FUNCTION IF EXISTS kg_guard_contract_frozen();
"""


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        ('branches', '0002_branch_tenancy_guard'),
        ('children', '0012_merge_20261003_0746'),
        ('organizations', '0002_organization_logo'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name='ContractTemplate',
            fields=[
                ('id', models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ('created_at', models.DateTimeField(auto_now_add=True, db_index=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('is_active', models.BooleanField(db_index=True, default=True)),
                ('name', models.CharField(max_length=150)),
                ('language', models.CharField(default='uz', max_length=2)),
                ('body', models.TextField()),
                ('version', models.PositiveIntegerField(default=1)),
                ('organization', models.ForeignKey(editable=False, on_delete=django.db.models.deletion.RESTRICT, related_name='%(app_label)s_%(class)s_set', to='organizations.organization')),
            ],
            options={
                'db_table': 'contract_template',
                'ordering': ['name'],
            },
        ),
        migrations.CreateModel(
            name='Contract',
            fields=[
                ('id', models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ('created_at', models.DateTimeField(auto_now_add=True, db_index=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('is_active', models.BooleanField(db_index=True, default=True)),
                ('number', models.CharField(max_length=30)),
                ('template_version', models.PositiveIntegerField()),
                ('values', models.JSONField(default=dict)),
                ('rendered_text', models.TextField()),
                ('status', models.CharField(choices=[('draft', 'Qoralama'), ('signed', 'Imzolangan'), ('terminated', 'Bekor qilingan')], default='draft', max_length=12)),
                ('signed_on', models.DateField(blank=True, null=True)),
                ('terminated_on', models.DateField(blank=True, null=True)),
                ('termination_reason', models.CharField(blank=True, max_length=255)),
                ('branch', models.ForeignKey(on_delete=django.db.models.deletion.RESTRICT, related_name='%(app_label)s_%(class)s_set', to='branches.branch')),
                ('child', models.ForeignKey(on_delete=django.db.models.deletion.RESTRICT, related_name='contracts', to='children.child')),
                ('created_by', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='+', to=settings.AUTH_USER_MODEL)),
                ('guardian', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.RESTRICT, related_name='contracts', to='children.guardian')),
                ('organization', models.ForeignKey(editable=False, on_delete=django.db.models.deletion.RESTRICT, related_name='%(app_label)s_%(class)s_set', to='organizations.organization')),
                ('template', models.ForeignKey(on_delete=django.db.models.deletion.RESTRICT, related_name='contracts', to='contracts.contracttemplate')),
            ],
            options={
                'db_table': 'contract',
                'ordering': ['-created_at'],
            },
        ),
        migrations.AddConstraint(
            model_name='contracttemplate',
            constraint=models.UniqueConstraint(condition=models.Q(('is_active', True)), fields=('organization', 'name'), name='uq_contract_template_name'),
        ),
        migrations.AddConstraint(
            model_name='contracttemplate',
            constraint=models.CheckConstraint(condition=models.Q(('language__in', ['uz', 'ru', 'en'])), name='ck_contract_template_language'),
        ),
        migrations.AddIndex(
            model_name='contract',
            index=models.Index(fields=['child', '-created_at'], name='ix_contract_child'),
        ),
        migrations.AddConstraint(
            model_name='contract',
            constraint=models.UniqueConstraint(fields=('organization', 'number'), name='uq_contract_number'),
        ),
        migrations.AddConstraint(
            model_name='contract',
            constraint=models.CheckConstraint(condition=models.Q(('status__in', ['draft', 'signed', 'terminated'])), name='ck_contract_status'),
        ),
        migrations.AddConstraint(
            model_name='contract',
            constraint=models.CheckConstraint(condition=models.Q(models.Q(('signed_on__isnull', True), ('status', 'draft')), models.Q(('signed_on__isnull', False), ('status', 'signed')), ('status', 'terminated'), _connector='OR'), name='ck_contract_signed_on'),
        ),
        migrations.AddConstraint(
            model_name='contract',
            constraint=models.CheckConstraint(condition=models.Q(models.Q(('status', 'terminated'), ('terminated_on__isnull', False)), models.Q(models.Q(('status', 'terminated'), _negated=True), ('terminated_on__isnull', True)), _connector='OR'), name='ck_contract_terminated_on'),
        ),
        *attach_tenant_guards("contract_template"),
        migrations.RunSQL(
            sql=policy_sql_for("contract_template"),
            reverse_sql=teardown_sql_for("contract_template"),
        ),
        *attach_tenant_guards("contract"),
        migrations.RunSQL(sql=policy_sql_for("contract"), reverse_sql=teardown_sql_for("contract")),
        migrations.RunSQL(sql=FROZEN_SQL, reverse_sql=FROZEN_REVERSE),
    ]
