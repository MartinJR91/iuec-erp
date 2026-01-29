from __future__ import annotations

from django.db import migrations, models
import django.db.models.deletion


def _seed_default_faculty(apps, schema_editor) -> None:
    Faculty = apps.get_model("academic", "Faculty")
    Program = apps.get_model("academic", "Program")

    faculty, _ = Faculty.objects.get_or_create(
        code="GEN",
        defaults={"name": "Faculté Générale", "tutelle": "MINESUP", "is_active": True},
    )
    Program.objects.filter(faculty__isnull=True).update(faculty=faculty)


class Migration(migrations.Migration):
    dependencies = [
        ("academic", "0001_initial"),
        ("identity", "0001_initial"),
    ]

    operations = [
        migrations.CreateModel(
            name="Faculty",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("code", models.CharField(max_length=16, unique=True)),
                ("name", models.CharField(max_length=150)),
                ("tutelle", models.CharField(blank=True, max_length=150)),
                ("is_active", models.BooleanField(default=True)),
                (
                    "doyen_uuid",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="faculties_led",
                        to="core_identity.coreidentity",
                        db_column="doyen_uuid",
                    ),
                ),
            ],
            options={"db_table": "FACULTY"},
        ),
        migrations.RenameField(
            model_name="program",
            old_name="label",
            new_name="name",
        ),
        migrations.AddField(
            model_name="program",
            name="faculty",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.PROTECT,
                related_name="programs",
                to="academic.faculty",
            ),
        ),
        migrations.RunPython(_seed_default_faculty, migrations.RunPython.noop),
        migrations.AlterField(
            model_name="program",
            name="faculty",
            field=models.ForeignKey(
                on_delete=django.db.models.deletion.PROTECT,
                related_name="programs",
                to="academic.faculty",
            ),
        ),
    ]
