"""
Service de calcul des échéances de frais pour les étudiants.
"""

from __future__ import annotations

from datetime import date, datetime, timedelta
from decimal import Decimal
from typing import Any, Dict, List, Optional

from django.db.models import Q, Sum
from django.utils import timezone

from apps.academic.models import Bourse, Frais, RegistrationAdmin, StudentProfile
from apps.finance.models import Invoice, Payment


class FraisEcheanceCalculator:
    """Calcule les échéances de frais pour un étudiant."""

    def calculer_echeances(
        self,
        student: StudentProfile,
        date_reference: Optional[date] = None,
        academic_year: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Calcule les échéances pour un étudiant.

        Args:
            student: Profil étudiant
            date_reference: Date de référence pour le calcul (par défaut aujourd'hui)
            academic_year: Année académique (par défaut année active)

        Returns:
            Dict avec tranches, montant_dû, prochaine_échéance, statut, jours_retard
        """
        if date_reference is None:
            date_reference = timezone.now().date()

        # Récupérer l'inscription active
        registration = RegistrationAdmin.objects.filter(
            student=student
        ).order_by("-registration_date").first()

        if not registration:
            return {
                "tranches": [],
                "montant_du": Decimal("0"),
                "prochaine_echeance": None,
                "statut": "Aucune inscription",
                "jours_retard": 0,
            }

        # Utiliser l'année académique de l'inscription si non fournie
        if academic_year is None:
            academic_year = registration.academic_year.code

        # Récupérer les frais du programme
        if not student.current_program:
            return {
                "tranches": [],
                "montant_du": Decimal("0"),
                "prochaine_echeance": None,
                "statut": "Aucun programme assigné",
                "jours_retard": 0,
            }

        frais = Frais.objects.filter(
            program=student.current_program,
            academic_year=academic_year,
        ).first()

        if not frais:
            # Essayer depuis academic_rules_json
            rules = student.current_program.academic_rules_json
            if "frais" not in rules:
                return {
                    "tranches": [],
                    "montant_du": Decimal("0"),
                    "prochaine_echeance": None,
                    "statut": "Aucun frais configuré",
                    "jours_retard": 0,
                }
            frais_data = rules["frais"]
        else:
            frais_data = {
                "inscription": {
                    "total": float(frais.inscription_total),
                    "echeance": frais.echeance_inscription.isoformat() if frais.echeance_inscription else None,
                },
                "scolarite": {
                    "tranche1": float(frais.scolarite_tranche1),
                    "tranche2": float(frais.scolarite_tranche2),
                    "tranche3": float(frais.scolarite_tranche3) if frais.scolarite_tranche3 else None,
                    "total": float(frais.scolarite_total),
                    "echeances": frais.echeances_scolarite,
                },
                "autres": frais.autres_frais or {},
            }

        # Construire les tranches
        tranches = []

        # Frais d'inscription
        inscription_total = Decimal(str(frais_data.get("inscription", {}).get("total", 0)))
        if inscription_total > 0:
            echeance_inscription_str = frais_data.get("inscription", {}).get("echeance")
            echeance_inscription = None
            if echeance_inscription_str:
                try:
                    echeance_inscription = datetime.fromisoformat(echeance_inscription_str).date()
                except (ValueError, TypeError):
                    pass

            if echeance_inscription:
                tranches.append({
                    "type": "inscription",
                    "label": "Frais d'inscription",
                    "montant": inscription_total,
                    "echeance": echeance_inscription.isoformat(),
                    "due": date_reference >= echeance_inscription,
                    "payee": False,  # Sera mis à jour plus tard
                })

        # Frais de scolarité
        scolarite_data = frais_data.get("scolarite", {})
        echeances_scolarite = scolarite_data.get("echeances", [])

        # Si pas d'échéances dans le JSON, utiliser des dates par défaut
        if not echeances_scolarite:
            # Dates par défaut pour l'année académique
            year = date_reference.year
            echeances_scolarite = [
                f"{year}-10-30",  # Tranche 1 : 30 octobre
                f"{year}-12-14",  # Tranche 2 : 14 décembre
                f"{year + 1}-03-28",  # Tranche 3 : 28 mars année suivante
            ]

        tranche1_montant = Decimal(str(scolarite_data.get("tranche1", 0)))
        tranche2_montant = Decimal(str(scolarite_data.get("tranche2", 0)))
        tranche3_montant = Decimal(str(scolarite_data.get("tranche3", 0))) if scolarite_data.get("tranche3") else None

        if tranche1_montant > 0 and len(echeances_scolarite) > 0:
            echeance1 = self._parse_date(echeances_scolarite[0])
            if echeance1:
                tranches.append({
                    "type": "scolarite",
                    "label": "Scolarité - Tranche 1",
                    "montant": tranche1_montant,
                    "echeance": echeance1.isoformat(),
                    "due": date_reference >= echeance1,
                    "payee": False,
                })

        if tranche2_montant > 0 and len(echeances_scolarite) > 1:
            echeance2 = self._parse_date(echeances_scolarite[1])
            if echeance2:
                tranches.append({
                    "type": "scolarite",
                    "label": "Scolarité - Tranche 2",
                    "montant": tranche2_montant,
                    "echeance": echeance2.isoformat(),
                    "due": date_reference >= echeance2,
                    "payee": False,
                })

        if tranche3_montant and tranche3_montant > 0 and len(echeances_scolarite) > 2:
            echeance3 = self._parse_date(echeances_scolarite[2])
            if echeance3:
                tranches.append({
                    "type": "scolarite",
                    "label": "Scolarité - Tranche 3",
                    "montant": tranche3_montant,
                    "echeance": echeance3.isoformat(),
                    "due": date_reference >= echeance3,
                    "payee": False,
                })

        # Autres frais (kits, etc.) - considérés comme dus immédiatement
        autres_frais = frais_data.get("autres", {})
        autres_total = Decimal("0")
        for key, value in autres_frais.items():
            montant = Decimal(str(value)) if isinstance(value, (int, float, str)) else Decimal("0")
            autres_total += montant
            if montant > 0:
                tranches.append({
                    "type": "autres",
                    "label": f"Autres frais - {key}",
                    "montant": montant,
                    "echeance": date_reference.isoformat(),  # Dû immédiatement
                    "due": True,
                    "payee": False,
                })

        # Calculer les paiements déjà effectués
        total_paye = self._calculer_total_paye(student.identity_id)

        # Marquer les tranches payées et calculer le montant dû
        montant_du = Decimal("0")
        montant_restant = total_paye

        for tranche in tranches:
            if montant_restant >= tranche["montant"]:
                tranche["payee"] = True
                montant_restant -= tranche["montant"]
            elif montant_restant > 0:
                # Paiement partiel
                tranche["payee"] = False
                tranche["montant_restant"] = tranche["montant"] - montant_restant
                montant_restant = Decimal("0")
            else:
                tranche["payee"] = False
                tranche["montant_restant"] = tranche["montant"]

            if tranche["due"] and not tranche["payee"]:
                montant_du += tranche.get("montant_restant", tranche["montant"])

        # Déterminer la prochaine échéance
        prochaine_echeance = None
        prochaine_echeance_date = None
        for tranche in sorted(tranches, key=lambda t: t["echeance"]):
            if not tranche["payee"] and (prochaine_echeance_date is None or tranche["echeance"] < prochaine_echeance_date):
                prochaine_echeance = tranche["echeance"]
                prochaine_echeance_date = tranche["echeance"]

        # Calculer le statut et les jours de retard
        statut = "À jour"
        jours_retard = 0

        if montant_du > 0:
            # Trouver la première échéance en retard
            for tranche in sorted(tranches, key=lambda t: t["echeance"]):
                if tranche["due"] and not tranche["payee"]:
                    echeance_date = datetime.fromisoformat(tranche["echeance"]).date()
                    jours_retard = (date_reference - echeance_date).days

                    if jours_retard > 30:
                        statut = "Retard grave"
                    elif jours_retard > 0:
                        statut = f"En retard de {jours_retard} jours"
                    elif jours_retard >= -7:
                        statut = f"Échéance prochaine : {tranche['echeance']}"
                    break

        return {
            "tranches": tranches,
            "montant_du": float(montant_du),
            "prochaine_echeance": prochaine_echeance,
            "statut": statut,
            "jours_retard": jours_retard,
            "total_paye": float(total_paye),
        }

    def _parse_date(self, date_str: str) -> Optional[date]:
        """Parse une date depuis une string (ISO format ou autre)."""
        if not date_str:
            return None
        try:
            # Essayer ISO format
            return datetime.fromisoformat(date_str.replace("Z", "+00:00")).date()
        except (ValueError, AttributeError):
            try:
                # Essayer format DD/MM/YYYY
                return datetime.strptime(date_str, "%d/%m/%Y").date()
            except (ValueError, AttributeError):
                return None

    def _calculer_total_paye(self, identity_id) -> Decimal:
        """Calcule le total des paiements pour une identité."""
        total = (
            Payment.objects.filter(invoice__identity_uuid=identity_id)
            .aggregate(total=Sum("amount"))["total"]
            or Decimal("0")
        )
        return total

    def update_solde_etudiant(self, student: StudentProfile) -> None:
        """
        Met à jour le solde et le statut financier d'un étudiant.

        Recalcule le solde = total_frais - sum(payments) - sum(bourses_actives)
        Met à jour finance_status :
        - 'OK' si solde <= 0
        - 'Bloqué' si solde < -50000
        - 'Moratoire' sinon (si déjà en moratoire, garde le statut)
        """
        # Calculer le total des factures
        total_factures = (
            Invoice.objects.filter(identity_uuid=student.identity_id)
            .aggregate(total=Sum("total_amount"))["total"]
            or Decimal("0")
        )

        # Calculer le total des paiements
        total_paye = self._calculer_total_paye(student.identity_id)

        # Calculer le total des bourses actives pour cet étudiant
        total_bourses_actives = (
            Bourse.objects.filter(
                student=student,
                statut=Bourse.StatutChoices.ACTIVE
            )
            .aggregate(total=Sum("montant"))["total"]
            or Decimal("0")
        )

        # Solde = factures - paiements - bourses actives (négatif = dette)
        solde = total_factures - total_paye - total_bourses_actives

        # Mettre à jour le solde
        student.solde = solde

        # Mettre à jour le statut financier
        if solde <= 0:
            if student.finance_status != "Moratoire":
                student.finance_status = "OK"
        elif solde < Decimal("-50000"):
            student.finance_status = "Bloqué"
        # Si solde > -50000 et <= 0, garder le statut actuel (peut être Moratoire)

        student.save(update_fields=["solde", "finance_status"])
