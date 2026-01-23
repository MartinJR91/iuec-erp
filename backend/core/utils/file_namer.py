from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass
from datetime import date
from typing import Dict, Optional


_NON_ALNUM = re.compile(r"[^A-Z0-9_]+")
_UNDERSCORE = re.compile(r"_+")


def _normalize(value: str) -> str:
    normalized = unicodedata.normalize("NFKD", value)
    ascii_only = normalized.encode("ascii", "ignore").decode("ascii")
    replaced = ascii_only.replace(" ", "_").upper()
    cleaned = _NON_ALNUM.sub("_", replaced)
    collapsed = _UNDERSCORE.sub("_", cleaned).strip("_")
    return collapsed


@dataclass(frozen=True)
class FileNamingResult:
    filename: str
    pdfa_profile: Optional[str]


class FileNamer:
    """Génère des noms de fichiers selon la charte ERP."""

    PDF_PROFILE_FINAL = "PDF/A-3b"

    def generate(
        self,
        *,
        doc_type: str,
        entity: str,
        reference: str,
        detail: str,
        extension: str = "pdf",
        issued_on: Optional[date] = None,
        final: bool = True,
    ) -> FileNamingResult:
        issued_on = issued_on or date.today()
        parts = [
            issued_on.strftime("%Y_%m%d"),
            _normalize(doc_type),
            _normalize(entity),
            _normalize(reference),
            _normalize(detail),
        ]
        filename = f"{'_'.join(parts)}.{_normalize(extension).lower()}"
        pdfa_profile = self.PDF_PROFILE_FINAL if final and extension.lower() == "pdf" else None
        return FileNamingResult(filename=filename, pdfa_profile=pdfa_profile)

    @staticmethod
    def examples() -> Dict[str, str]:
        """Exemples de noms pour documents ERP."""
        return {
            "RELEVE": "2026_0123_RELEVE_ETUDIANT_ETU12345_SEM1.pdf",
            "FACT": "2026_0123_FACT_SCOL_ETU12345_FRAIS.pdf",
            "RECU": "2026_0123_RECU_SCOL_ETU12345_PAIEMENT.pdf",
            "PV_JURY": "2026_0123_PV_JURY_FAC_SCIENCES_S1.pdf",
            "CONTRAT": "2026_0123_CONTRAT_RH_AGENT42_CDD.pdf",
        }
