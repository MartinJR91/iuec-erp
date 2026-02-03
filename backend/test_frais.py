"""Script pour tester les frais importés."""
from apps.academic.models import Frais, Program

print("=== Résumé des frais importés ===\n")
print(f"Total instances Frais: {Frais.objects.count()}\n")

print("Par année académique:")
for year in Frais.objects.values_list('academic_year', flat=True).distinct():
    count = Frais.objects.filter(academic_year=year).count()
    print(f"  {year}: {count} programmes")

print(f"\nProgrammes avec frais de scolarité:")
print(f"  {Frais.objects.filter(scolarite_total__gt=0).count()} programmes")

print("\n=== Exemples de frais ===\n")

# Exemple 1: Frais d'inscription
f_inscription = Frais.objects.filter(inscription_total__gt=0).first()
if f_inscription:
    print(f"1. Frais d'inscription ({f_inscription.program.code}):")
    print(f"   - IUEC: {f_inscription.inscription_iuec} XAF")
    print(f"   - Tutelle: {f_inscription.inscription_tutelle} XAF")
    print(f"   - Total: {f_inscription.inscription_total} XAF")
    print(f"   - Échéance: {f_inscription.echeance_inscription}")

# Exemple 2: Frais de scolarité
f_scolarite = Frais.objects.filter(scolarite_total__gt=0).first()
if f_scolarite:
    print(f"\n2. Frais de scolarité ({f_scolarite.program.code}):")
    print(f"   - Tranche 1: {f_scolarite.scolarite_tranche1} XAF")
    print(f"   - Tranche 2: {f_scolarite.scolarite_tranche2} XAF")
    if f_scolarite.scolarite_tranche3:
        print(f"   - Tranche 3: {f_scolarite.scolarite_tranche3} XAF")
    print(f"   - Total: {f_scolarite.scolarite_total} XAF")
    print(f"   - Échéances: {f_scolarite.echeances_scolarite}")

# Exemple 3: Vérifier dans academic_rules_json
p = Program.objects.filter(code="FST_GENERAL").first()
if p and "frais" in p.academic_rules_json:
    print(f"\n3. Frais dans academic_rules_json (Programme {p.code}):")
    frais_data = p.academic_rules_json["frais"]
    if "inscription" in frais_data:
        print(f"   - Inscription: {frais_data['inscription']}")
    if "scolarite" in frais_data:
        print(f"   - Scolarité: {frais_data['scolarite']}")

print("\n=== Test terminé ===")
