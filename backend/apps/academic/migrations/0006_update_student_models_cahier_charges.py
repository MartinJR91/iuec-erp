# Generated manually for cahier des charges updates

import django.core.validators
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('academic', '0005_evaluation_grade'),
    ]

    operations = [
        # Renommer matricule en matricule_permanent
        migrations.RenameField(
            model_name='studentprofile',
            old_name='matricule',
            new_name='matricule_permanent',
        ),
        # Renommer program en current_program et rendre nullable
        migrations.RenameField(
            model_name='studentprofile',
            old_name='program',
            new_name='current_program',
        ),
        migrations.AlterField(
            model_name='studentprofile',
            name='current_program',
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.PROTECT,
                related_name='students',
                to='academic.program',
                db_column='current_program_id',
            ),
        ),
        # Ajouter academic_status
        migrations.AddField(
            model_name='studentprofile',
            name='academic_status',
            field=models.CharField(
                choices=[('ACTIF', 'Actif'), ('AJOURE', 'Ajourné'), ('EXCLU', 'Exclu')],
                default='ACTIF',
                max_length=16,
            ),
        ),
        # Renommer identity en identity_uuid (db_column seulement)
        migrations.AlterField(
            model_name='studentprofile',
            name='identity',
            field=models.OneToOneField(
                on_delete=django.db.models.deletion.CASCADE,
                related_name='student_profile',
                to='core_identity.coreidentity',
                db_column='identity_uuid',
            ),
        ),
        # Renommer year en academic_year dans RegistrationAdmin
        migrations.RenameField(
            model_name='registrationadmin',
            old_name='year',
            new_name='academic_year',
        ),
        migrations.AlterField(
            model_name='registrationadmin',
            name='academic_year',
            field=models.ForeignKey(
                on_delete=django.db.models.deletion.PROTECT,
                related_name='registrations',
                to='academic.academicyear',
                db_column='academic_year_id',
            ),
        ),
        # Ajouter registration_date
        migrations.AddField(
            model_name='registrationadmin',
            name='registration_date',
            field=models.DateTimeField(auto_now_add=True, null=True),
        ),
        # Renommer student en student_uuid (db_column seulement)
        migrations.AlterField(
            model_name='registrationadmin',
            name='student',
            field=models.ForeignKey(
                on_delete=django.db.models.deletion.CASCADE,
                related_name='registrations',
                to='academic.studentprofile',
                db_column='student_uuid',
            ),
        ),
        # Ajouter contrainte CheckConstraint pour bloquer les inscriptions si finance_status = 'BLOQUE'
        migrations.AddConstraint(
            model_name='registrationadmin',
            constraint=models.CheckConstraint(
                check=~models.Q(finance_status='BLOQUE'),
                name='no_registration_if_blocked',
            ),
        ),
        # Renommer registration en registration_admin dans RegistrationPedagogical
        migrations.RenameField(
            model_name='registrationpedagogical',
            old_name='registration',
            new_name='registration_admin',
        ),
        migrations.AlterField(
            model_name='registrationpedagogical',
            name='registration_admin',
            field=models.ForeignKey(
                on_delete=django.db.models.deletion.CASCADE,
                related_name='teaching_units',
                to='academic.registrationadmin',
                db_column='registration_admin_id',
            ),
        ),
        # Renommer teaching_unit_id en teaching_unit
        migrations.RenameField(
            model_name='registrationpedagogical',
            old_name='teaching_unit_id',
            new_name='teaching_unit',
        ),
        migrations.AlterField(
            model_name='registrationpedagogical',
            name='teaching_unit',
            field=models.UUIDField(db_column='teaching_unit_id'),
        ),
        # Modifier les choix de status pour inclure 'EN_COURS' et 'DETTE'
        migrations.AlterField(
            model_name='registrationpedagogical',
            name='status',
            field=models.CharField(
                choices=[
                    ('EN_COURS', 'En cours'),
                    ('VALIDE', 'Validé'),
                    ('AJOURE', 'Ajourné'),
                    ('DETTE', 'Dette'),
                ],
                default='EN_COURS',
                max_length=16,
            ),
        ),
    ]
