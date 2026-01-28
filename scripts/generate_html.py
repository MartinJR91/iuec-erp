#!/usr/bin/env python3
"""
Script pour générer un HTML formaté à partir du Markdown de déploiement Render.
Le HTML peut être imprimé en PDF depuis le navigateur (Ctrl+P > Enregistrer en PDF).
"""

import re
from pathlib import Path

BASE_DIR = Path(__file__).parent.parent
MD_FILE = BASE_DIR / "docs" / "DEPLOIEMENT_RENDER_COMPLET.md"
HTML_FILE = BASE_DIR / "docs" / "DEPLOIEMENT_RENDER_COMPLET.html"


def markdown_to_html(md_content: str) -> str:
    """Convertir Markdown en HTML basique."""
    html = md_content
    
    # Titres
    html = re.sub(r'^# (.+)$', r'<h1>\1</h1>', html, flags=re.MULTILINE)
    html = re.sub(r'^## (.+)$', r'<h2>\1</h2>', html, flags=re.MULTILINE)
    html = re.sub(r'^### (.+)$', r'<h3>\1</h3>', html, flags=re.MULTILINE)
    
    # Code blocks
    html = re.sub(
        r'```(\w+)?\n(.*?)```',
        r'<pre><code class="language-\1">\2</code></pre>',
        html,
        flags=re.DOTALL
    )
    
    # Inline code
    html = re.sub(r'`([^`]+)`', r'<code>\1</code>', html)
    
    # Listes à puces
    html = re.sub(r'^- (.+)$', r'<li>\1</li>', html, flags=re.MULTILINE)
    html = re.sub(r'(<li>.*</li>)', r'<ul>\1</ul>', html, flags=re.DOTALL)
    
    # Listes numérotées
    html = re.sub(r'^\d+\. (.+)$', r'<li>\1</li>', html, flags=re.MULTILINE)
    
    # Gras
    html = re.sub(r'\*\*([^*]+)\*\*', r'<strong>\1</strong>', html)
    
    # Italique
    html = re.sub(r'\*([^*]+)\*', r'<em>\1</em>', html)
    
    # Séparateurs
    html = re.sub(r'^---$', r'<hr>', html, flags=re.MULTILINE)
    
    # Paragraphes (lignes non vides)
    lines = html.split('\n')
    result = []
    in_code = False
    
    for line in lines:
        if '<pre>' in line:
            in_code = True
        if '</pre>' in line:
            in_code = False
        
        if not in_code and line.strip() and not line.strip().startswith('<'):
            result.append(f'<p>{line}</p>')
        else:
            result.append(line)
    
    html = '\n'.join(result)
    
    return html


def generate_html():
    """Générer le HTML à partir du Markdown."""
    if not MD_FILE.exists():
        print(f"ERREUR: Fichier Markdown introuvable: {MD_FILE}")
        return
    
    print(f"Lecture du Markdown: {MD_FILE}")
    with open(MD_FILE, "r", encoding="utf-8") as f:
        md_content = f.read()
    
    html_body = markdown_to_html(md_content)
    
    html_template = f"""<!DOCTYPE html>
<html lang="fr">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Guide Complet de Déploiement IUEC-ERP sur Render</title>
    <style>
        @page {{
            margin: 2cm;
            size: A4;
        }}
        body {{
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            line-height: 1.6;
            color: #333;
            max-width: 900px;
            margin: 0 auto;
            padding: 20px;
            background: #fff;
        }}
        h1 {{
            color: #1a1a1a;
            font-size: 28px;
            border-bottom: 3px solid #2c3e50;
            padding-bottom: 10px;
            margin-top: 30px;
            page-break-after: avoid;
        }}
        h2 {{
            color: #2c3e50;
            font-size: 20px;
            margin-top: 25px;
            margin-bottom: 15px;
            page-break-after: avoid;
        }}
        h3 {{
            color: #34495e;
            font-size: 16px;
            margin-top: 20px;
            margin-bottom: 10px;
            page-break-after: avoid;
        }}
        p {{
            margin: 10px 0;
            text-align: justify;
        }}
        code {{
            background: #f4f4f4;
            padding: 2px 6px;
            border-radius: 3px;
            font-family: 'Courier New', monospace;
            font-size: 0.9em;
            color: #c7254e;
        }}
        pre {{
            background: #f8f8f8;
            border: 1px solid #ddd;
            border-left: 4px solid #2c3e50;
            padding: 15px;
            overflow-x: auto;
            margin: 15px 0;
            page-break-inside: avoid;
        }}
        pre code {{
            background: none;
            padding: 0;
            color: #333;
            font-size: 0.85em;
        }}
        ul, ol {{
            margin: 15px 0;
            padding-left: 30px;
        }}
        li {{
            margin: 5px 0;
        }}
        hr {{
            border: none;
            border-top: 2px solid #ddd;
            margin: 30px 0;
        }}
        strong {{
            color: #2c3e50;
            font-weight: 600;
        }}
        .header {{
            text-align: center;
            margin-bottom: 40px;
            padding-bottom: 20px;
            border-bottom: 2px solid #2c3e50;
        }}
        .header h1 {{
            border: none;
            margin: 0;
        }}
        .meta {{
            color: #666;
            font-size: 0.9em;
            margin-top: 10px;
        }}
        @media print {{
            body {{
                padding: 0;
            }}
            h1, h2, h3 {{
                page-break-after: avoid;
            }}
            pre {{
                page-break-inside: avoid;
            }}
        }}
    </style>
</head>
<body>
    <div class="header">
        <h1>Guide Complet de Déploiement<br>IUEC-ERP sur Render</h1>
        <div class="meta">
            <strong>Date de création</strong> : 27 janvier 2026<br>
            <strong>Version</strong> : 1.0<br>
            <strong>Auteur</strong> : Documentation technique IUEC-ERP
        </div>
    </div>
    
    {html_body}
    
    <hr>
    <div style="text-align: center; color: #666; font-size: 0.9em; margin-top: 40px;">
        <p><strong>Document généré le</strong> : 27 janvier 2026 | <strong>Version</strong> : 1.0</p>
        <p>Pour imprimer en PDF : Ctrl+P > Enregistrer en PDF</p>
    </div>
</body>
</html>"""
    
    print(f"Génération du HTML: {HTML_FILE}")
    with open(HTML_FILE, "w", encoding="utf-8") as f:
        f.write(html_template)
    
    print(f"HTML genere avec succes: {HTML_FILE}")
    print("\nPour convertir en PDF:")
    print("   1. Ouvrez le fichier HTML dans votre navigateur")
    print("   2. Appuyez sur Ctrl+P (ou Cmd+P sur Mac)")
    print("   3. Selectionnez 'Enregistrer en PDF' comme destination")
    print("   4. Cliquez sur 'Enregistrer'")


if __name__ == "__main__":
    generate_html()
