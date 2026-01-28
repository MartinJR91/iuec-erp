#!/usr/bin/env python3
"""
Script pour générer un PDF à partir du Markdown de déploiement Render.
Utilise reportlab pour créer un PDF formaté.
"""

import os
import sys
from pathlib import Path

try:
    from reportlab.lib.pagesizes import A4
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.lib.units import inch
    from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, PageBreak, Table, TableStyle
    from reportlab.lib import colors
    from reportlab.lib.enums import TA_LEFT, TA_CENTER, TA_JUSTIFY
except ImportError:
    print("ERREUR: reportlab n'est pas installé.")
    print("Installez-le avec: pip install reportlab")
    sys.exit(1)

# Chemins
BASE_DIR = Path(__file__).parent.parent
MD_FILE = BASE_DIR / "docs" / "DEPLOIEMENT_RENDER_COMPLET.md"
PDF_FILE = BASE_DIR / "docs" / "DEPLOIEMENT_RENDER_COMPLET.pdf"


def read_markdown(file_path: Path) -> str:
    """Lire le fichier Markdown."""
    with open(file_path, "r", encoding="utf-8") as f:
        return f.read()


def parse_markdown_to_elements(md_content: str, styles):
    """Parser le Markdown et créer des éléments reportlab."""
    elements = []
    lines = md_content.split("\n")
    
    i = 0
    while i < len(lines):
        line = lines[i].strip()
        
        # Titre niveau 1
        if line.startswith("# ") and not line.startswith("##"):
            title = line[2:].strip()
            elements.append(Spacer(1, 0.3 * inch))
            elements.append(Paragraph(title, styles["Title"]))
            elements.append(Spacer(1, 0.2 * inch))
        
        # Titre niveau 2
        elif line.startswith("## "):
            title = line[3:].strip()
            elements.append(Spacer(1, 0.2 * inch))
            elements.append(Paragraph(title, styles["Heading1"]))
            elements.append(Spacer(1, 0.1 * inch))
        
        # Titre niveau 3
        elif line.startswith("### "):
            title = line[4:].strip()
            elements.append(Spacer(1, 0.15 * inch))
            elements.append(Paragraph(title, styles["Heading2"]))
            elements.append(Spacer(1, 0.05 * inch))
        
        # Code block
        elif line.startswith("```"):
            code_lines = []
            i += 1
            while i < len(lines) and not lines[i].strip().startswith("```"):
                code_lines.append(lines[i])
                i += 1
            code_text = "\n".join(code_lines)
            # Style code simple
            code_style = ParagraphStyle(
                "Code",
                parent=styles["Normal"],
                fontName="Courier",
                fontSize=8,
                leftIndent=0.5 * inch,
                backColor=colors.lightgrey,
                borderPadding=5,
            )
            elements.append(Paragraph(f"<font face='Courier' size='8'>{code_text}</font>", code_style))
            elements.append(Spacer(1, 0.1 * inch))
        
        # Liste à puces
        elif line.startswith("- "):
            bullet_text = line[2:].strip()
            elements.append(Paragraph(f"• {bullet_text}", styles["Normal"]))
        
        # Liste numérotée
        elif line and line[0].isdigit() and ". " in line[:5]:
            num, text = line.split(". ", 1)
            elements.append(Paragraph(f"{num}. {text}", styles["Normal"]))
        
        # Ligne vide
        elif not line:
            elements.append(Spacer(1, 0.05 * inch))
        
        # Paragraphe normal
        elif line and not line.startswith("**") and not line.startswith("---"):
            # Échapper HTML pour reportlab
            para_text = line.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
            # Formatage basique
            para_text = para_text.replace("**", "<b>").replace("**", "</b>")
            para_text = para_text.replace("`", "<font face='Courier' size='9'>").replace("`", "</font>")
            elements.append(Paragraph(para_text, styles["Normal"]))
            elements.append(Spacer(1, 0.05 * inch))
        
        # Séparateur
        elif line.startswith("---"):
            elements.append(Spacer(1, 0.2 * inch))
        
        i += 1
    
    return elements


def generate_pdf():
    """Générer le PDF à partir du Markdown."""
    if not MD_FILE.exists():
        print(f"ERREUR: Fichier Markdown introuvable: {MD_FILE}")
        sys.exit(1)
    
    print(f"Lecture du Markdown: {MD_FILE}")
    md_content = read_markdown(MD_FILE)
    
    print(f"Génération du PDF: {PDF_FILE}")
    doc = SimpleDocTemplate(
        str(PDF_FILE),
        pagesize=A4,
        rightMargin=72,
        leftMargin=72,
        topMargin=72,
        bottomMargin=18,
    )
    
    # Styles
    styles = getSampleStyleSheet()
    styles.add(ParagraphStyle(
        "Title",
        parent=styles["Title"],
        fontSize=24,
        textColor=colors.HexColor("#1a1a1a"),
        spaceAfter=30,
        alignment=TA_CENTER,
    ))
    styles.add(ParagraphStyle(
        "Heading1",
        parent=styles["Heading1"],
        fontSize=16,
        textColor=colors.HexColor("#2c3e50"),
        spaceAfter=12,
    ))
    styles.add(ParagraphStyle(
        "Heading2",
        parent=styles["Heading2"],
        fontSize=14,
        textColor=colors.HexColor("#34495e"),
        spaceAfter=8,
    ))
    
    # Parser et créer éléments
    elements = parse_markdown_to_elements(md_content, styles)
    
    # Construire PDF
    doc.build(elements)
    print(f"✅ PDF généré avec succès: {PDF_FILE}")


if __name__ == "__main__":
    generate_pdf()
