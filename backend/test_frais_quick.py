"""Script rapide pour tester les frais."""
import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings')
django.setup()

from apps.academic.models import Frais, Program

print("=== Test des frais importes ===\n")
print(f"Total Frais: {Frais.objects.count()}\n")

# Exemple
f = Frais.objects.filter(scolarite_total__gt=0).first()
if f:
    print(f"Exemple - Programme: {f.program.code}")
    print(f"  Scolarite: {f.scolarite_total} XAF")
    print(f"  Inscription: {f.inscription_total} XAF")

# Verifier dans rules_json
p = Program.objects.filter(code="FST_GENERAL").first()
if p:
    has_frais = "frais" in p.academic_rules_json
    print(f"\nProgramme FST_GENERAL a frais dans rules_json: {has_frais}")

print("\n[OK] Test termine")
