from decimal import Decimal

from django.db import migrations, models


def configure_recommended_limits(apps, schema_editor):
    EventBudget = apps.get_model("news", "EventBudget")
    AutomaticUpdateSchedule = apps.get_model("news", "AutomaticUpdateSchedule")
    budget = EventBudget.objects.filter(pk=1).first()
    if budget:
        if budget.max_cost_gbp_per_day == Decimal("2.00"):
            budget.max_cost_gbp_per_day = Decimal("0.75")
        if budget.max_cost_gbp_per_month == Decimal("30.00"):
            budget.max_cost_gbp_per_month = Decimal("20.00")
        budget.save(update_fields=["max_cost_gbp_per_day", "max_cost_gbp_per_month"])
    AutomaticUpdateSchedule.objects.get_or_create(
        pk=1,
        defaults={
            "enabled": True,
            "timezone_name": "Europe/Bucharest",
            "start_hour": 8,
            "end_hour": 21,
            "interval_hours": 1,
        },
    )


class Migration(migrations.Migration):
    dependencies = [("news", "0014_remove_reporting_language_from_confirmed_facts")]

    operations = [
        migrations.CreateModel(
            name="AutomaticUpdateSchedule",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("enabled", models.BooleanField(default=True, verbose_name="Rulare activă")),
                ("timezone_name", models.CharField(default="Europe/Bucharest", max_length=64, verbose_name="Fus orar")),
                ("start_hour", models.PositiveSmallIntegerField(default=8, verbose_name="Prima rulare (ora)")),
                ("end_hour", models.PositiveSmallIntegerField(default=21, verbose_name="Ultima rulare (ora)")),
                ("interval_hours", models.PositiveSmallIntegerField(default=1, verbose_name="Interval între rulări (ore)")),
                ("updated_at", models.DateTimeField(auto_now=True)),
            ],
            options={
                "verbose_name": "Program rulare automată",
                "verbose_name_plural": "Program rulare automată",
            },
        ),
        migrations.AlterField(
            model_name="eventbudget",
            name="max_cost_gbp_per_day",
            field=models.DecimalField(decimal_places=2, default=Decimal("0.75"), max_digits=10),
        ),
        migrations.AlterField(
            model_name="eventbudget",
            name="max_cost_gbp_per_month",
            field=models.DecimalField(decimal_places=2, default=Decimal("20.00"), max_digits=10),
        ),
        migrations.RunPython(configure_recommended_limits, migrations.RunPython.noop),
    ]
