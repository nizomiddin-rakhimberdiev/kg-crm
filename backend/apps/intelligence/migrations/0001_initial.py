"""
Radix Intelligence: `insight` jadvali + RLS siyosati (docs/07 §10).

Siyosat SHU YERDA qo'yiladi, `core/0002` da emas: u migratsiya yangi
o'rnatishda bu jadval hali yaratilmagan paytda ishlaydi (va `to_regclass`
himoyasi tufayli `insight` ni o'tkazib yuboradi). `check_rls` esa uni
39-jadval sifatida talab qiladi — ikkalasi birga: jadval bor → siyosat bor.
"""

import uuid

import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models

from apps.core.rls import policy_sql_for, teardown_sql_for


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        ("branches", "0002_branch_tenancy_guard"),
        ("organizations", "0001_initial"),
        # RLS funksiyalari (`app_current_org()`) core/0002 da yaratiladi.
        ("core", "0002_row_level_security"),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name='Insight',
            fields=[
                ('id', models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ('created_at', models.DateTimeField(auto_now_add=True, db_index=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('is_active', models.BooleanField(db_index=True, default=True)),
                ('type', models.CharField(choices=[('payment_delay', "To'lov kechikishi"), ('attendance_drop', 'Davomat pasayishi')], max_length=40)),
                ('severity', models.CharField(choices=[('warning', 'Ogohlantirish'), ('critical', 'Jiddiy')], max_length=10)),
                ('status', models.CharField(choices=[('new', 'Yangi'), ('seen', "Ko'rilgan"), ('resolved', 'Hal qilingan'), ('dismissed', 'Rad etilgan'), ('auto_resolved', "O'zi hal bo'lgan")], default='new', max_length=14)),
                ('subject_type', models.CharField(choices=[('branch', 'Filial'), ('group', 'Guruh')], max_length=20)),
                ('subject_id', models.UUIDField()),
                ('evidence', models.JSONField()),
                ('evidence_version', models.PositiveSmallIntegerField(default=1)),
                ('recommendation_key', models.CharField(max_length=60)),
                ('deep_link', models.CharField(max_length=200)),
                ('generated_at', models.DateTimeField()),
                ('refreshed_at', models.DateTimeField(blank=True, null=True)),
                ('seen_at', models.DateTimeField(blank=True, null=True)),
                ('resolved_at', models.DateTimeField(blank=True, null=True)),
                ('dismissed_at', models.DateTimeField(blank=True, null=True)),
                ('dismissed_until', models.DateTimeField(blank=True, null=True)),
                ('auto_resolved_at', models.DateTimeField(blank=True, null=True)),
                ('acted_by', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='+', to=settings.AUTH_USER_MODEL)),
                ('branch', models.ForeignKey(on_delete=django.db.models.deletion.RESTRICT, related_name='%(app_label)s_%(class)s_set', to='branches.branch')),
                ('organization', models.ForeignKey(editable=False, on_delete=django.db.models.deletion.RESTRICT, related_name='%(app_label)s_%(class)s_set', to='organizations.organization')),
            ],
            options={
                'db_table': 'insight',
                'ordering': ['-severity', '-generated_at'],
                'indexes': [models.Index(condition=models.Q(('status__in', ('new', 'seen'))), fields=['organization', 'branch', 'severity'], name='ix_insight_open'), models.Index(fields=['branch', 'type', '-generated_at'], name='ix_insight_history'), models.Index(condition=models.Q(('status', 'dismissed')), fields=['branch', 'type', 'subject_type', 'subject_id', 'dismissed_until'], name='ix_insight_suppression')],
                'constraints': [models.UniqueConstraint(condition=models.Q(('status__in', ('new', 'seen'))), fields=('branch', 'type', 'subject_type', 'subject_id'), name='uq_insight_open_condition'), models.CheckConstraint(condition=models.Q(('status__in', ['new', 'seen', 'resolved', 'dismissed', 'auto_resolved'])), name='ck_insight_status'), models.CheckConstraint(condition=models.Q(('severity__in', ['warning', 'critical'])), name='ck_insight_severity'), models.CheckConstraint(condition=models.Q(models.Q(('subject_id', models.F('branch_id')), ('subject_type', 'branch')), ('subject_type', 'group'), _connector='OR'), name='ck_insight_branch_subject_is_branch'), models.CheckConstraint(condition=models.Q(('dismissed_until__isnull', True), ('status', 'dismissed'), _connector='OR'), name='ck_insight_dismissed_until_only_when_dismissed'), models.CheckConstraint(condition=models.Q(models.Q(('auto_resolved_at__isnull', True), ('dismissed_at__isnull', True), ('resolved_at__isnull', True), ('status__in', ('new', 'seen'))), models.Q(('auto_resolved_at__isnull', True), ('dismissed_at__isnull', True), ('resolved_at__isnull', False), ('status', 'resolved')), models.Q(('auto_resolved_at__isnull', True), ('dismissed_at__isnull', False), ('resolved_at__isnull', True), ('status', 'dismissed')), models.Q(('auto_resolved_at__isnull', False), ('dismissed_at__isnull', True), ('resolved_at__isnull', True), ('status', 'auto_resolved')), _connector='OR'), name='ck_insight_exactly_one_closing_timestamp')],
            },
        ),
        migrations.RunSQL(sql=policy_sql_for("insight"), reverse_sql=teardown_sql_for("insight")),
    ]
