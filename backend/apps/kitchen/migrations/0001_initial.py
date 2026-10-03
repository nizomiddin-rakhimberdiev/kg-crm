"""
Kitchen (PLAN 6.6): dishes with per-portion ingredients, and the daily menu.
Four tenant tables with the standard guards and RLS (`check_rls` 54 -> 58).
Stock itself never changes here — serving writes `stock_movement` rows.
"""

import django.db.models.deletion
import uuid
from decimal import Decimal
from django.conf import settings
from django.db import migrations, models

from apps.core.db import attach_tenant_guards
from apps.core.rls import policy_sql_for, teardown_sql_for

TABLES = ("dish", "dish_ingredient", "menu_day", "menu_item")


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        ('branches', '0002_branch_tenancy_guard'),
        ('inventory', '0004_alter_stockmovement_movement_type'),
        ('organizations', '0002_organization_logo'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name='Dish',
            fields=[
                ('id', models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ('created_at', models.DateTimeField(auto_now_add=True, db_index=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('is_active', models.BooleanField(db_index=True, default=True)),
                ('name', models.CharField(max_length=150)),
                ('portion_grams', models.PositiveIntegerField(blank=True, null=True)),
                ('note', models.CharField(blank=True, max_length=255)),
                ('branch', models.ForeignKey(on_delete=django.db.models.deletion.RESTRICT, related_name='%(app_label)s_%(class)s_set', to='branches.branch')),
                ('organization', models.ForeignKey(editable=False, on_delete=django.db.models.deletion.RESTRICT, related_name='%(app_label)s_%(class)s_set', to='organizations.organization')),
            ],
            options={
                'db_table': 'dish',
                'ordering': ['name'],
            },
        ),
        migrations.CreateModel(
            name='DishIngredient',
            fields=[
                ('id', models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ('created_at', models.DateTimeField(auto_now_add=True, db_index=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('is_active', models.BooleanField(db_index=True, default=True)),
                ('quantity_per_portion', models.DecimalField(decimal_places=3, max_digits=10)),
                ('branch', models.ForeignKey(on_delete=django.db.models.deletion.RESTRICT, related_name='%(app_label)s_%(class)s_set', to='branches.branch')),
                ('dish', models.ForeignKey(on_delete=django.db.models.deletion.RESTRICT, related_name='ingredients', to='kitchen.dish')),
                ('organization', models.ForeignKey(editable=False, on_delete=django.db.models.deletion.RESTRICT, related_name='%(app_label)s_%(class)s_set', to='organizations.organization')),
                ('product', models.ForeignKey(on_delete=django.db.models.deletion.RESTRICT, related_name='dish_ingredients', to='inventory.product')),
            ],
            options={
                'db_table': 'dish_ingredient',
            },
        ),
        migrations.CreateModel(
            name='MenuDay',
            fields=[
                ('id', models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ('created_at', models.DateTimeField(auto_now_add=True, db_index=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('is_active', models.BooleanField(db_index=True, default=True)),
                ('menu_date', models.DateField()),
                ('status', models.CharField(choices=[('draft', 'Reja'), ('served', 'Berildi')], default='draft', max_length=10)),
                ('children_portions', models.PositiveIntegerField(blank=True, null=True)),
                ('staff_portions', models.PositiveIntegerField(default=0)),
                ('served_at', models.DateTimeField(blank=True, null=True)),
                ('branch', models.ForeignKey(on_delete=django.db.models.deletion.RESTRICT, related_name='%(app_label)s_%(class)s_set', to='branches.branch')),
                ('organization', models.ForeignKey(editable=False, on_delete=django.db.models.deletion.RESTRICT, related_name='%(app_label)s_%(class)s_set', to='organizations.organization')),
                ('served_by', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='+', to=settings.AUTH_USER_MODEL)),
                ('warehouse', models.ForeignKey(on_delete=django.db.models.deletion.RESTRICT, related_name='menu_days', to='inventory.warehouse')),
            ],
            options={
                'db_table': 'menu_day',
                'ordering': ['-menu_date'],
            },
        ),
        migrations.CreateModel(
            name='MenuItem',
            fields=[
                ('id', models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ('created_at', models.DateTimeField(auto_now_add=True, db_index=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('is_active', models.BooleanField(db_index=True, default=True)),
                ('meal', models.CharField(choices=[('breakfast', 'Nonushta'), ('lunch', 'Tushlik'), ('snack', 'Poldnik'), ('dinner', 'Kechki ovqat')], max_length=10)),
                ('branch', models.ForeignKey(on_delete=django.db.models.deletion.RESTRICT, related_name='%(app_label)s_%(class)s_set', to='branches.branch')),
                ('dish', models.ForeignKey(on_delete=django.db.models.deletion.RESTRICT, related_name='menu_items', to='kitchen.dish')),
                ('menu_day', models.ForeignKey(on_delete=django.db.models.deletion.RESTRICT, related_name='items', to='kitchen.menuday')),
                ('organization', models.ForeignKey(editable=False, on_delete=django.db.models.deletion.RESTRICT, related_name='%(app_label)s_%(class)s_set', to='organizations.organization')),
            ],
            options={
                'db_table': 'menu_item',
            },
        ),
        migrations.AddConstraint(
            model_name='dish',
            constraint=models.UniqueConstraint(condition=models.Q(('is_active', True)), fields=('branch', 'name'), name='uq_dish_name'),
        ),
        migrations.AddConstraint(
            model_name='dishingredient',
            constraint=models.UniqueConstraint(fields=('dish', 'product'), name='uq_dish_ingredient'),
        ),
        migrations.AddConstraint(
            model_name='dishingredient',
            constraint=models.CheckConstraint(condition=models.Q(('quantity_per_portion__gt', Decimal('0'))), name='ck_dish_ingredient_quantity'),
        ),
        migrations.AddConstraint(
            model_name='menuday',
            constraint=models.UniqueConstraint(fields=('branch', 'menu_date'), name='uq_menu_day_branch_date'),
        ),
        migrations.AddConstraint(
            model_name='menuday',
            constraint=models.CheckConstraint(condition=models.Q(('status__in', ['draft', 'served'])), name='ck_menu_day_status'),
        ),
        migrations.AddConstraint(
            model_name='menuday',
            constraint=models.CheckConstraint(condition=models.Q(models.Q(('served_at__isnull', True), ('status', 'draft')), models.Q(('served_at__isnull', False), ('status', 'served')), _connector='OR'), name='ck_menu_day_served_at'),
        ),
        migrations.AddConstraint(
            model_name='menuitem',
            constraint=models.UniqueConstraint(fields=('menu_day', 'dish', 'meal'), name='uq_menu_item'),
        ),
        migrations.AddConstraint(
            model_name='menuitem',
            constraint=models.CheckConstraint(condition=models.Q(('meal__in', ['breakfast', 'lunch', 'snack', 'dinner'])), name='ck_menu_item_meal'),
        ),
        *[guard for table in TABLES for guard in attach_tenant_guards(table)],
        *[
            migrations.RunSQL(sql=policy_sql_for(table), reverse_sql=teardown_sql_for(table))
            for table in TABLES
        ],
    ]
