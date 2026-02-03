"""Commande pour importer les frais depuis un JSON."""
from __future__ import annotations

import json
from datetime import datetime
from decimal import Decimal, InvalidOperation
from typing import Any, Dict, List

from django.core.management.base import BaseCommand
from django.utils.dateparse import parse_date

from apps.academic.models import Faculty, Frais, Program


def parse_date_fr(date_str: str) -> datetime | None:
    """Parse une date au format français (ex: '18 octobre 2024')."""
    if not date_str:
        return None
    
    # Mapping des mois français
    mois_fr = {
        "janvier": "01", "février": "02", "fevrier": "02", "mars": "03",
        "avril": "04", "mai": "05", "juin": "06", "juillet": "07",
        "août": "08", "aout": "08", "septembre": "09", "octobre": "10",
        "novembre": "11", "décembre": "12", "decembre": "12",
    }
    
    try:
        parts = date_str.strip().split()
        if len(parts) >= 3:
            jour = parts[0].zfill(2)
            mois_str = parts[1].lower()
            annee = parts[2]
            mois = mois_fr.get(mois_str, "01")
            date_iso = f"{annee}-{mois}-{jour}"
            return parse_date(date_iso)
    except Exception:
        pass
    
    return None


def find_or_create_program(
    faculty_code: str,
    program_name: str,
    program_code: str | None = None,
) -> Program:
    """Trouve ou crée un programme."""
    faculty, _ = Faculty.objects.get_or_create(
        code=faculty_code,
        defaults={"name": f"Faculté {faculty_code}", "is_active": True},
    )
    
    if not program_code:
        # Générer un code à partir du nom
        program_code = program_name.upper().replace(" ", "_")[:32]
    
    program, created = Program.objects.get_or_create(
        code=program_code,
        defaults={
            "name": program_name,
            "faculty": faculty,
            "academic_rules_json": {
                "grading_system": {
                    "min_validate": 10,
                    "compensation": True,
                    "elimination_mark": 10,
                    "blocking_components": [],
                },
                "financial_rules": {},
            },
            "is_active": True,
        },
    )
    
    if created:
        print(f"  [OK] Programme cree: {program.code} - {program.name}")
    else:
        print(f"  [->] Programme existant: {program.code} - {program.name}")
    
    return program


def import_frais_inscription(
    data: Dict[str, Any],
    academic_year: str,
) -> None:
    """Importe les frais d'inscription généraux."""
    frais_inscription = data.get("frais_inscription_generaux", {})
    echeance_generale = frais_inscription.get("echeance_generale", "")
    echeance_date = parse_date_fr(echeance_generale)
    
    par_faculte = frais_inscription.get("par_faculte", {})
    
    for fac_code, frais_data in par_faculte.items():
        # Trouver ou créer un programme générique pour cette faculté
        program = find_or_create_program(
            faculty_code=fac_code,
            program_name=f"Programme général {fac_code}",
            program_code=f"{fac_code}_GENERAL",
        )
        
        frais, created = Frais.objects.update_or_create(
            program=program,
            academic_year=academic_year,
            defaults={
                "inscription_iuec": Decimal(str(frais_data.get("iuec", 0))),
                "inscription_tutelle": Decimal(str(frais_data.get("tutelle", 0))),
                "inscription_total": Decimal(str(frais_data.get("total", 0))),
                "echeance_inscription": echeance_date,
            },
        )
        
        # Mettre à jour academic_rules_json avec les frais
        rules = program.academic_rules_json
        if "frais" not in rules:
            rules["frais"] = {}
        rules["frais"]["inscription"] = {
            "iuec": float(frais.inscription_iuec),
            "tutelle": float(frais.inscription_tutelle),
            "total": float(frais.inscription_total),
            "echeance": echeance_generale,
        }
        program.academic_rules_json = rules
        program.save()
        
        action = "cree" if created else "mis a jour"
        print(f"    [OK] Frais d'inscription {action} pour {fac_code}")


def import_frais_scolarite(
    data: Dict[str, Any],
    academic_year: str,
) -> None:
    """Importe les frais de scolarité par faculté/filière."""
    frais_scolarite = data.get("frais_scolarite", {})
    
    for fac_code, fac_data in frais_scolarite.items():
        for niveau, niveau_data in fac_data.items():
            # Niveau peut être "Licence", "Master_Professionnel", "Master", etc.
            # Vérifier si niveau_data est directement un dict avec specialites (cas FASE, FSE)
            if isinstance(niveau_data, dict) and "specialites" in niveau_data:
                # Cas où les spécialités sont directement au niveau du niveau (FASE, FSE)
                specialites = niveau_data.get("specialites", [])
                tranche1 = niveau_data.get("tranche1", 0)
                tranche2 = niveau_data.get("tranche2", 0)
                tranche3 = niveau_data.get("tranche3", 0)
                total = niveau_data.get("total", 0)
                echeances = niveau_data.get("echeances", [])
                
                # Vérifier si les tranches sont des listes (cas BTS)
                if isinstance(tranche1, list):
                    # Ce cas devrait être géré dans la boucle principale, skip
                    continue
                
                # Créer un programme pour chaque spécialité
                for specialite in specialites:
                    program_name = f"{niveau} {specialite}"
                    program_code = f"{fac_code}_{niveau}_{specialite}".replace(" ", "_")[:32]
                    
                    program = find_or_create_program(
                        faculty_code=fac_code,
                        program_name=program_name,
                        program_code=program_code,
                    )
                    
                    # Convertir en Decimal de manière sécurisée
                    defaults = {
                        "scolarite_tranche1": Decimal(str(int(float(tranche1)))),
                        "scolarite_tranche2": Decimal(str(int(float(tranche2)))),
                        "scolarite_total": Decimal(str(int(float(total)))),
                        "echeances_scolarite": echeances,
                    }
                    if tranche3:
                        try:
                            defaults["scolarite_tranche3"] = Decimal(str(int(float(tranche3))))
                        except (ValueError, TypeError, InvalidOperation):
                            pass
                    
                    frais, created = Frais.objects.update_or_create(
                        program=program,
                        academic_year=academic_year,
                        defaults=defaults,
                    )
                    
                    # Mettre à jour academic_rules_json
                    rules = program.academic_rules_json
                    if "frais" not in rules:
                        rules["frais"] = {}
                    rules["frais"]["scolarite"] = {
                        "tranche1": float(frais.scolarite_tranche1),
                        "tranche2": float(frais.scolarite_tranche2),
                        "tranche3": float(frais.scolarite_tranche3) if frais.scolarite_tranche3 else None,
                        "total": float(frais.scolarite_total),
                        "echeances": echeances,
                    }
                    program.academic_rules_json = rules
                    program.save()
                    
                    action = "cree" if created else "mis a jour"
                    print(f"    [OK] Frais scolarite {action} pour {program.code}")
                continue
            
            # Cas normal : niveau_data contient des sous-catégories (FST, BTS)
            if not isinstance(niveau_data, dict):
                continue
                
            for specialite_key, specialite_data in niveau_data.items():
                if specialite_key == "specialites":
                    # Cas où specialites est au même niveau
                    continue
                
                if not isinstance(specialite_data, dict):
                    continue
                
                specialites = specialite_data.get("specialites", [])
                tranche1 = specialite_data.get("tranche1", 0)
                tranche2 = specialite_data.get("tranche2", 0)
                tranche3 = specialite_data.get("tranche3", 0)
                total = specialite_data.get("total", 0)
                echeances = specialite_data.get("echeances", [])
                
                # Gérer les cas où tranche1/tranche2/tranche3/total sont des listes (BTS)
                if isinstance(tranche1, list):
                    # Pour chaque spécialité, créer un programme
                    for idx, specialite in enumerate(specialites):
                        program_name = f"{niveau} {specialite}"
                        program_code = f"{fac_code}_{niveau}_{specialite_key}_{idx}".replace(" ", "_")[:32]
                        
                        program = find_or_create_program(
                            faculty_code=fac_code,
                            program_name=program_name,
                            program_code=program_code,
                        )
                        
                        echeances_dates = [parse_date_fr(e) for e in echeances]
                        
                        try:
                            # Extraire les valeurs de manière sécurisée
                            if isinstance(tranche1, list):
                                val_t1 = tranche1[idx] if idx < len(tranche1) else 0
                            else:
                                val_t1 = tranche1
                            
                            if isinstance(tranche2, list):
                                val_t2 = tranche2[idx] if idx < len(tranche2) else 0
                            else:
                                val_t2 = tranche2
                            
                            val_t3 = None
                            if tranche3:
                                if isinstance(tranche3, list):
                                    val_t3 = tranche3[idx] if idx < len(tranche3) else None
                                else:
                                    val_t3 = tranche3
                            
                            if isinstance(total, list):
                                val_total = total[idx] if idx < len(total) else 0
                            else:
                                val_total = total
                            
                            # Convertir en Decimal de manière sécurisée
                            defaults = {
                                "scolarite_tranche1": Decimal(str(int(float(val_t1)))),
                                "scolarite_tranche2": Decimal(str(int(float(val_t2)))),
                                "scolarite_total": Decimal(str(int(float(val_total)))),
                                "echeances_scolarite": echeances,
                            }
                            if val_t3 is not None:
                                try:
                                    defaults["scolarite_tranche3"] = Decimal(str(int(float(val_t3))))
                                except (ValueError, TypeError):
                                    pass  # Ignorer si conversion échoue
                            
                            frais, created = Frais.objects.update_or_create(
                                program=program,
                                academic_year=academic_year,
                                defaults=defaults,
                            )
                        except (ValueError, IndexError, TypeError, InvalidOperation, Exception) as e:
                            print(f"    [ERREUR] Impossible de traiter les frais pour {specialite}: {e}")
                            print(f"      tranche1={tranche1} (type: {type(tranche1)}), tranche2={tranche2}, tranche3={tranche3}, total={total}, idx={idx}")
                            import traceback
                            traceback.print_exc()
                            continue
                        
                            # Mettre à jour academic_rules_json
                            rules = program.academic_rules_json
                            if "frais" not in rules:
                                rules["frais"] = {}
                            rules["frais"]["scolarite"] = {
                                "tranche1": float(frais.scolarite_tranche1),
                                "tranche2": float(frais.scolarite_tranche2),
                                "tranche3": float(frais.scolarite_tranche3) if frais.scolarite_tranche3 else None,
                                "total": float(frais.scolarite_total),
                                "echeances": echeances,
                            }
                            program.academic_rules_json = rules
                            program.save()
                            
                            action = "cree" if created else "mis a jour"
                            print(f"    [OK] Frais scolarite {action} pour {program.code}")
                else:
                    # Cas normal : une seule valeur par tranche
                    # Créer un programme pour chaque spécialité ou un programme global
                    if specialites:
                        for specialite in specialites:
                            program_name = f"{niveau} {specialite}"
                            program_code = f"{fac_code}_{niveau}_{specialite_key}_{specialite}".replace(" ", "_")[:32]
                            
                            program = find_or_create_program(
                                faculty_code=fac_code,
                                program_name=program_name,
                                program_code=program_code,
                            )
                            
                            echeances_dates = [parse_date_fr(e) for e in echeances]
                            
                            frais, created = Frais.objects.update_or_create(
                                program=program,
                                academic_year=academic_year,
                                defaults={
                                    "scolarite_tranche1": Decimal(str(tranche1)),
                                    "scolarite_tranche2": Decimal(str(tranche2)),
                                    "scolarite_tranche3": Decimal(str(tranche3)) if tranche3 else None,
                                    "scolarite_total": Decimal(str(total)),
                                    "echeances_scolarite": echeances,
                                },
                            )
                            
                            # Mettre à jour academic_rules_json
                            rules = program.academic_rules_json
                            if "frais" not in rules:
                                rules["frais"] = {}
                            rules["frais"]["scolarite"] = {
                                "tranche1": float(frais.scolarite_tranche1),
                                "tranche2": float(frais.scolarite_tranche2),
                                "tranche3": float(frais.scolarite_tranche3) if frais.scolarite_tranche3 else None,
                                "total": float(frais.scolarite_total),
                                "echeances": echeances,
                            }
                            program.academic_rules_json = rules
                            program.save()
                            
                            action = "cree" if created else "mis a jour"
                            print(f"    [OK] Frais scolarite {action} pour {program.code}")
                    else:
                        # Pas de spécialités, créer un programme global pour le niveau
                        program_name = f"{niveau} {specialite_key}"
                        program_code = f"{fac_code}_{niveau}_{specialite_key}".replace(" ", "_")[:32]
                        
                        program = find_or_create_program(
                            faculty_code=fac_code,
                            program_name=program_name,
                            program_code=program_code,
                        )
                        
                        frais, created = Frais.objects.update_or_create(
                            program=program,
                            academic_year=academic_year,
                            defaults={
                                "scolarite_tranche1": Decimal(str(tranche1)),
                                "scolarite_tranche2": Decimal(str(tranche2)),
                                "scolarite_tranche3": Decimal(str(tranche3)) if tranche3 else None,
                                "scolarite_total": Decimal(str(total)),
                                "echeances_scolarite": echeances,
                            },
                        )
                        
                        # Mettre à jour academic_rules_json
                        rules = program.academic_rules_json
                        if "frais" not in rules:
                            rules["frais"] = {}
                        rules["frais"]["scolarite"] = {
                            "tranche1": float(frais.scolarite_tranche1),
                            "tranche2": float(frais.scolarite_tranche2),
                            "tranche3": float(frais.scolarite_tranche3) if frais.scolarite_tranche3 else None,
                            "total": float(frais.scolarite_total),
                            "echeances": echeances,
                        }
                        program.academic_rules_json = rules
                        program.save()
                        
        action = "cree" if created else "mis a jour"
        print(f"    [OK] Frais scolarite {action} pour {program.code}")


def import_autres_frais(
    data: Dict[str, Any],
    academic_year: str,
) -> None:
    """Importe les autres frais (kits, blouses, etc.) dans les programmes existants."""
    autres_frais = data.get("autres_frais", {})
    
    # Mettre à jour tous les programmes avec les autres frais
    for program in Program.objects.all():
        rules = program.academic_rules_json
        if "frais" not in rules:
            rules["frais"] = {}
        
        # Ajouter les autres frais généraux
        if "autres" not in rules["frais"]:
            rules["frais"]["autres"] = {}
        
        rules["frais"]["autres"].update(autres_frais)
        
        # Mettre à jour l'instance Frais si elle existe
        frais = Frais.objects.filter(program=program, academic_year=academic_year).first()
        if frais:
            frais.autres_frais = autres_frais
            frais.save()
        else:
            # Créer une instance Frais avec seulement autres_frais
            Frais.objects.create(
                program=program,
                academic_year=academic_year,
                autres_frais=autres_frais,
            )
        
        program.academic_rules_json = rules
        program.save()
    
        print(f"  [OK] Autres frais mis a jour pour tous les programmes")


class Command(BaseCommand):
    help = "Importe les frais depuis un JSON collé dans le code."

    def add_arguments(self, parser):
        parser.add_argument(
            "--json-data",
            type=str,
            help="JSON data as string (optional, uses embedded data if not provided)",
        )

    def handle(self, *args, **options):
        # JSON fourni par l'utilisateur
        json_data_str = options.get("json_data") or """[{
  "academic_year": "2024-2025",
  "frais_inscription_generaux": {
    "echeance_generale": "18 octobre 2024",
    "par_faculte": {
      "FST": { "iuec": 15000, "tutelle": 50000, "total": 65000 },
      "FASE": { "iuec": 15000, "tutelle": 50000, "total": 65000 },
      "FSE": { "iuec": 15000, "tutelle": 50000, "total": 65000 },
      "BTS": { "iuec": 20000, "tutelle": 0, "total": 20000 },
      "Capacite_Droit": { "iuec": 10000, "tutelle": 50000, "total": 60000 }
    }
  },
  "frais_scolarite": {
    "FST": {
      "Licence_Professionnel": {
        "Sciences_Biomedicales": {
          "specialites": ["Biologie clinique", "Santé Publique", "Nutrition et Diététique", "Pharmacologie"],
          "tranche1": 320000, "tranche2": 160000, "tranche3": 160000, "total": 640000,
          "echeances": ["30 octobre 2024", "14 décembre 2024", "28 mars 2025"]
        },
        "Sciences_Medicosanitaires": {
          "specialites": ["Analyses Médicales", "Sciences infirmières", "Santé de reproduction"],
          "tranche1": 300000, "tranche2": 130000, "tranche3": 125000, "total": 555000,
          "echeances": ["30 octobre 2024", "14 décembre 2024", "28 mars 2025"]
        },
        "Ingenierie_Biomedicale_Energetique": {
          "specialites": ["Contrôle qualité et certification", "Ingénierie énergétique", "Ingénierie biomédicale"],
          "tranche1": 320000, "tranche2": 160000, "tranche3": 160000, "total": 640000,
          "echeances": ["30 octobre 2024", "14 décembre 2024", "28 mars 2025"]
        }
      },
      "Master_Professionnel": {
        "Sciences_Biomedicales": {
          "specialites": ["Cytopathologie Clinique", "Biologie Clinique Approfondie", "Santé Publique et Epidémiologie", "Pharmacologie Clinique"],
          "tranche1": 400000, "tranche2": 350000, "tranche3": 0, "total": 750000,
          "echeances": ["30 octobre 2024", "14 décembre 2024"]
        }
      }
    },
    "FASE": {
      "Licence": {
        "specialites": ["Technologie alimentaires et biotechnologies", "Production animale", "Production végétale"],
        "tranche1": 250000, "tranche2": 125000, "tranche3": 125000, "total": 500000,
        "echeances": ["30 octobre 2024", "14 décembre 2024", "28 mars 2025"]
      },
      "Master_Professionnel": {
        "specialites": ["Production animale", "Production végétale"],
        "tranche1": 350000, "tranche2": 250000, "tranche3": 0, "total": 600000,
        "echeances": ["30 octobre 2024", "14 décembre 2024"]
      }
    },
    "FSE": {
      "Licence": {
        "specialites": ["Didactique des disciplines"],
        "tranche1": 150000, "tranche2": 100000, "tranche3": 50000, "total": 300000,
        "echeances": ["30 octobre 2024", "14 décembre 2024", "28 mars 2025"]
      },
      "Master": {
        "specialites": ["Pédagogie Active et Créative, Ingénierie de Formation et Qualité de l'éducation"],
        "tranche1": 300000, "tranche2": 300000, "tranche3": 0, "total": 600000,
        "echeances": ["30 octobre 2024", "14 décembre 2024"]
      }
    },
    "BTS": {
      "Professions_Medicales_Medicosanitaires": {
        "specialites": ["Soins infirmiers", "Kinésithérapie", "Santé de reproduction/Sage-femme", "Imagerie médicale", "Techniques de laboratoires d'analyses Médicales"],
        "tranche1": [200000, 250000, 250000, 250000, 250000], "tranche2": [100000, 125000, 125000, 125000, 125000], "tranche3": [100000, 125000, 125000, 125000, 125000], "total": [400000, 500000, 500000, 500000, 500000],
        "echeances": ["30 octobre 2024", "14 décembre 2024", "28 mars 2025"]
      },
      "Genie_Informatique": {
        "specialites": ["Génie logiciel", "Infographie et Web Design", "Maintenance des systèmes informatiques", "Télécommunication", "Réseaux et Sécurité"],
        "tranche1": 150000, "tranche2": 100000, "tranche3": 50000, "total": 300000,
        "echeances": ["30 octobre 2024", "14 décembre 2024", "28 mars 2025"]
      },
      "Commerce_Gestion": {
        "specialites": ["Commerce International", "Marketing-Commerce-Vente", "Banque et Finance", "Comptabilité et gestion des entreprises", "Gestion des projets", "Gestion Des Ressources Humaines", "Gestion logistique et transport"],
        "tranche1": 150000, "tranche2": 50000, "tranche3": 50000, "total": 250000,
        "echeances": ["30 octobre 2024", "14 décembre 2024", "28 mars 2025"]
      },
      "Agriculture_Elevage": {
        "specialites": ["Aquaculture", "Conseil Agropastoral", "Entreprenariat Agropastoral", "Production Animale"],
        "tranche1": 150000, "tranche2": 50000, "tranche3": 50000, "total": 250000,
        "echeances": ["30 octobre 2024", "14 décembre 2024", "28 mars 2025"]
      }
    }
  },
  "autres_frais": {
    "generaux": {
      "Blouse_frequentation": { "concerne": "Tous nouveaux étudiants", "utilite": "Identification", "cout": 6500 },
      "Matiere_oeuvre_FASE_BTS_Agropastorale": { "concerne": "Étudiants BTS Agropastorale", "utilite": "Activités pratiques", "cout": 50000 },
      "Kit_Agronome_FASE": { "concerne": "Nouveaux étudiants FASE", "utilite": "Tenue pratiques + sport + outils (casque, machette, etc.)", "cout": 30000 },
      "Kit_Professionnel_Sante_BTS": { "concerne": "Nouveaux étudiants BTS Santé", "utilite": "Kit santé (stéthoscope, etc.) + blouse obligatoire", "cout": 12500 },
      "Matiere_oeuvre_BTS": { "concerne": "Tous étudiants BTS", "utilite": "2 rames papier", "cout": 0, "echeance": "31 octobre 2024" }
    },
    "rattrapages": { "concerne": "Taux validation ≤70%", "cout": { "FST/FASE/FSE": 5000, "BTS/Capacite_Droit": 3000 }, "unite": "par UE" },
    "soutenances": {
      "Licence/Master/BTS_Sante": [45000, 30000, 30000, 80000, 100000],
      "Autres_BTS": [25000, 15000, 15000, 80000, 100000],
      "FSE": [30000, 80000, 150000],
      "FASE": [0, 0, 100000],
      "FST": [0, 30000, 100000]
    },
    "redoublement": { "concerne": "Tous redoublants", "frais": "Comme nouveau étudiant ou 50000 par UE reprise" },
    "chevauchement": { "BTS": 2500, "Licence": 5000, "unite": "par UE non validée", "echeances": ["30 octobre 2024 (semestre I)", "15 février 2025 (semestre II)"] }
  }
}]"""
        
        try:
            data_list = json.loads(json_data_str)
            
            if not isinstance(data_list, list) or len(data_list) == 0:
                self.stdout.write(self.style.ERROR("Le JSON doit être une liste non vide."))
                return
            
            for data in data_list:
                academic_year = data.get("academic_year", "2024-2025")
                self.stdout.write(self.style.SUCCESS(f"\n[Import] Frais pour l'annee {academic_year}"))
                
                # 1. Importer les frais d'inscription
                self.stdout.write("\n[1] Frais d'inscription...")
                import_frais_inscription(data, academic_year)
                
                # 2. Importer les frais de scolarité
                self.stdout.write("\n[2] Frais de scolarite...")
                import_frais_scolarite(data, academic_year)
                
                # 3. Importer les autres frais
                self.stdout.write("\n[3] Autres frais...")
                import_autres_frais(data, academic_year)
            
            self.stdout.write(self.style.SUCCESS("\n[OK] Import termine avec succes !"))
            
        except json.JSONDecodeError as e:
            self.stdout.write(self.style.ERROR(f"Erreur de parsing JSON: {e}"))
        except Exception as e:
            self.stdout.write(self.style.ERROR(f"Erreur lors de l'import: {e}"))
            import traceback
            self.stdout.write(traceback.format_exc())
