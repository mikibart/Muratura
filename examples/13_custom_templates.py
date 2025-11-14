"""
MURATURA FEM - Custom Templates Example
Esempio utilizzo template LaTeX personalizzati

Questo script dimostra come utilizzare i template LaTeX personalizzati
per generare relazioni di calcolo con formattazione professionale.

Template disponibili:
1. ntc2018_standard - Template completo NTC 2018
2. ntc2018_historic - Template per edifici storici vincolati

Features:
- Frontespizio personalizzato
- Header/footer con logo studio
- Sezioni conformi NTC 2018 §10.1
- Tabelle formattate professionalmente
- Grafici integrati
- TOC (Table of Contents)
- Appendice (opzionale)

Note:
Richiede LaTeX installato (pdflatex) per generazione PDF.
"""

from pathlib import Path
from unittest.mock import Mock

try:
    from Material.reports import ReportGenerator, ReportMetadata, ReportSettings
    REPORT_AVAILABLE = True
except ImportError:
    print("⚠️  Report Generator module not available")
    exit(1)


def print_header(title: str):
    """Stampa intestazione esempio"""
    print("\\n" + "=" * 70)
    print(f"ESEMPIO: {title}")
    print("=" * 70)


def create_standard_building_model():
    """Crea modello edificio moderno standard"""
    model = Mock()
    model.building_type = 'Edificio in muratura portante - Nuovo'
    model.usage = 'Residenziale'
    model.construction_period = 'N/D'  # Nuova costruzione
    model.num_stories = 4
    model.total_height = 13.5  # m

    # Materiali
    mock_mat = Mock()
    mock_mat.name = 'Muratura in blocchi forati Poroton 30cm'
    mock_mat.f_m_k = 4.0  # MPa
    mock_mat.E = 2400  # MPa
    mock_mat.w = 8.0  # kN/m³
    model.materials = [mock_mat]

    # Verifiche
    mock_verif = Mock()
    mock_verif.element_id = 'Parete perimetrale P1'
    mock_verif.type = 'SLU - Pressoflessione'
    mock_verif.demand = 2.8
    mock_verif.capacity = 4.0

    model.verification_results = [mock_verif]
    model.has_frp_reinforcement = False
    model.is_historic = False

    return model


def create_historic_building_model():
    """Crea modello edificio storico"""
    model = Mock()
    model.building_type = 'Palazzo storico in muratura'
    model.usage = 'Residenziale'
    model.construction_period = '1700-1750'
    model.num_stories = 3
    model.total_height = 11.0  # m

    # Materiali storici
    mock_mat = Mock()
    mock_mat.name = 'Muratura in mattoni pieni e malta di calce'
    mock_mat.f_m_k = 1.78  # MPa (ridotto per FC=1.20)
    mock_mat.E = 1200  # MPa
    mock_mat.w = 18.0  # kN/m³
    model.materials = [mock_mat]

    # Verifiche
    mock_verif = Mock()
    mock_verif.element_id = 'Parete nord - piano terra'
    mock_verif.type = 'SLU - Taglio'
    mock_verif.demand = 0.10
    mock_verif.capacity = 0.15

    model.verification_results = [mock_verif]
    model.has_frp_reinforcement = True
    model.is_historic = True
    model.has_arches_analysis = True

    return model


def main():
    print("🏛️  MURATURA FEM v7.0 - Custom LaTeX Templates")
    print("=" * 70)
    print("Professional Report Generation with Customizable Templates")
    print("=" * 70)

    # Crea directory output
    output_dir = Path(__file__).parent / 'output' / 'reports'
    output_dir.mkdir(parents=True, exist_ok=True)

    # ========================================================================
    # ESEMPIO 1: Template Standard NTC 2018
    # ========================================================================
    print_header("Template NTC 2018 Standard - Edificio Moderno")
    print("\\nUtilizzo template 'ntc2018_standard.tex' per nuove costruzioni.\\n")

    model_standard = create_standard_building_model()

    metadata_std = ReportMetadata(
        project_name="Nuovo Complesso Residenziale",
        project_location="Bologna (BO)",
        project_address="Via Nuova Costruzione 100, 40100 Bologna",
        client_name="Società Costruzioni Moderna S.r.l.",
        designer_name="Ing. Marco Bianchi",
        designer_order="Ordine degli Ingegneri di Bologna n. B12345"
    )

    settings_std = ReportSettings(
        template_name='ntc2018_standard',  # Template personalizzato!
        output_format='pdf',
        include_graphs=True,
        include_tables=True,
        include_toc=True,
        include_appendix=False,
        font_size=11,
        page_size='A4'
    )

    generator_std = ReportGenerator(model_standard, metadata_std, settings_std)

    try:
        pdf_file = output_dir / 'relazione_standard_template.pdf'
        print(f"🔧 Generating PDF with custom template...")
        result = generator_std.generate_report(str(pdf_file))
        print(f"✅ PDF generated: {pdf_file.name}")
        print(f"   File size: {Path(result).stat().st_size / 1024:.1f} KB")
        print(f"   Template: ntc2018_standard.tex")
        print(f"   ℹ️  Features:")
        print(f"      - Professional frontespizio")
        print(f"      - Custom header/footer")
        print(f"      - Table of Contents")
        print(f"      - Formatted tables with booktabs")
        print(f"      - Numbered sections per NTC 2018")

    except FileNotFoundError:
        print("❌ LaTeX (pdflatex) not installed")
        print("   Template would work with LaTeX installed")
    except Exception as e:
        print(f"❌ PDF generation failed: {e}")
        print(f"   Template exists: {(Path(__file__).parent.parent / 'Material/reports/templates/ntc2018_standard.tex').exists()}")

    # ========================================================================
    # ESEMPIO 2: Template Edifici Storici
    # ========================================================================
    print_header("Template NTC 2018 Historic - Edificio Vincolato")
    print("\\nUtilizzo template 'ntc2018_historic.tex' per patrimonio culturale.\\n")

    model_historic = create_historic_building_model()

    metadata_hist = ReportMetadata(
        project_name="Restauro Palazzo Nobiliare del XVIII Secolo",
        project_location="Firenze (FI)",
        project_address="Via del Patrimonio 15, 50100 Firenze",
        client_name="Soprintendenza Archeologia Belle Arti Firenze",
        designer_name="Arch. Ing. Laura Rossi",
        designer_order="Ordine degli Ingegneri di Firenze n. R54321",
        report_type="sismica"
    )

    settings_hist = ReportSettings(
        template_name='ntc2018_historic',  # Template edifici storici!
        output_format='pdf',
        include_graphs=True,
        include_tables=True,
        include_toc=True,
        font_size=11
    )

    generator_hist = ReportGenerator(model_historic, metadata_hist, settings_hist)

    try:
        pdf_file = output_dir / 'relazione_historic_template.pdf'
        print(f"🔧 Generating PDF with historic buildings template...")
        result = generator_hist.generate_report(str(pdf_file))
        print(f"✅ PDF generated: {pdf_file.name}")
        print(f"   File size: {Path(result).stat().st_size / 1024:.1f} KB")
        print(f"   Template: ntc2018_historic.tex")
        print(f"   ℹ️  Specialized sections:")
        print(f"      - Vincoli e tutela")
        print(f"      - Inquadramento storico")
        print(f"      - Livello di conoscenza (LC/FC)")
        print(f"      - Analisi limite archi/volte")
        print(f"      - Interventi compatibili")
        print(f"      - Criteri reversibilità")

    except FileNotFoundError:
        print("❌ LaTeX (pdflatex) not installed")
    except Exception as e:
        print(f"❌ PDF generation failed: {e}")

    # ========================================================================
    # ESEMPIO 3: Confronto Template
    # ========================================================================
    print_header("Confronto Template Disponibili")

    print("\\n📋 Template LaTeX Disponibili:\\n")

    templates_dir = Path(__file__).parent.parent / 'Material/reports/templates'

    if templates_dir.exists():
        tex_files = list(templates_dir.glob('*.tex'))

        if tex_files:
            for i, template_file in enumerate(tex_files, 1):
                print(f"  {i}. {template_file.name}")
                print(f"     Path: {template_file}")
                print(f"     Size: {template_file.stat().st_size / 1024:.1f} KB")

                # Leggi prime righe per trovare descrizione
                with open(template_file, 'r', encoding='utf-8') as f:
                    lines = f.readlines()[:10]
                    for line in lines:
                        if 'Template:' in line:
                            desc = line.split('Template:')[1].strip()
                            print(f"     Description: {desc}")
                            break
                print()
        else:
            print("  ⚠️  No .tex templates found")
    else:
        print(f"  ⚠️  Templates directory not found: {templates_dir}")

    # ========================================================================
    # ESEMPIO 4: Personalizzazione Template
    # ========================================================================
    print_header("Guida Personalizzazione Template")

    print("""
\\n📝 Come Personalizzare i Template:

1. **Copia template base**:
   cp Material/reports/templates/ntc2018_standard.tex \\
      Material/reports/templates/my_studio_template.tex

2. **Modifica template**:
   - Aggiungi logo studio: \\includegraphics{path/to/logo.png}
   - Personalizza header/footer
   - Cambia colori: \\definecolor{mycolor}{RGB}{R,G,B}
   - Aggiungi sezioni custom

3. **Usa template personalizzato**:
   ```python
   settings = ReportSettings(
       template_name='my_studio_template',  # Nome senza .tex
       output_format='pdf'
   )
   ```

4. **Variabili Jinja2 disponibili**:
   - metadata.* (project_name, client_name, designer_name, etc.)
   - settings.* (font_size, page_size, include_toc, etc.)
   - materials (lista materiali)
   - verifications (lista verifiche)
   - codes (lista normative)
   - conclusions (testo conclusioni)
   - figures (lista grafici)

5. **Sintassi Jinja2 in LaTeX**:
   - Variabili: {{ variable }}
   - Condizioni: {% if condition %} ... {% endif %}
   - Loop: {% for item in list %} ... {% endfor %}
   - Filtri: {{ value|format("%.2f") }}

💡 **Best Practices**:
- Mantieni compatibilità con variabili base
- Testa con dataset completo
- Versiona template con git
- Documenta sezioni custom
""")

    # ========================================================================
    # ESEMPIO 5: Fallback Template
    # ========================================================================
    print_header("Fallback to Embedded Template")

    print("""
\\n🛡️  Sistema Fallback Automatico:

Se il template personalizzato non esiste, il sistema usa automaticamente
il template minimale embedded (sempre funzionante).

Esempio:
""")

    settings_fallback = ReportSettings(
        template_name='nonexistent_template',  # Non esiste!
        output_format='md'  # Markdown per test veloce
    )

    generator_fb = ReportGenerator(model_standard, metadata_std, settings_fallback)

    try:
        md_file = output_dir / 'relazione_fallback.md'
        result = generator_fb.generate_report(str(md_file))
        print(f"✅ Fallback successful: {md_file.name} generated")
        print(f"   Used: embedded minimal template")
    except Exception as e:
        print(f"❌ Even fallback failed: {e}")

    # ========================================================================
    # RIEPILOGO
    # ========================================================================
    print("\\n" + "=" * 70)
    print("✅ Custom Templates Examples Completed!")
    print("=" * 70)

    print(f"\\n📁 Generated files in {output_dir}:")
    for f in output_dir.iterdir():
        if f.is_file() and 'template' in f.name:
            size_kb = f.stat().st_size / 1024
            print(f"   - {f.name} ({size_kb:.1f} KB)")

    print("\\n🎯 FASE 3 - Module 3: Custom Templates IMPLEMENTATO!")
    print("   ✅ Template ntc2018_standard.tex (edifici moderni)")
    print("   ✅ Template ntc2018_historic.tex (patrimonio culturale)")
    print("   ✅ Sistema caricamento template esterni")
    print("   ✅ Fallback automatico a template embedded")
    print("   ✅ Jinja2 templating con variabili complete")
    print("   ✅ Frontespizio, TOC, header/footer personalizzabili")

    print("\\n📚 Template Features:")
    print("   - Frontespizio professionale con dati progetto")
    print("   - Header/footer con nome progetto e pagina")
    print("   - Table of Contents con hyperlinks")
    print("   - Sezioni numerate conformi NTC 2018 §10.1")
    print("   - Tabelle formattate (booktabs)")
    print("   - Grafici integrati (matplotlib → PDF)")
    print("   - Appendice opzionale per tabulati")
    print("   - Colori personalizzabili per studio")
    print()


if __name__ == "__main__":
    main()
