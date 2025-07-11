import json
import logging
from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def wrap_text(text, max_width, style):
    """Wrap text to fit within a maximum width for a table cell."""
    return Paragraph(text, style)

def generate_pdf(json_path, pdf_output="compliance_report.pdf", product_name="Cefixime Tablets USP 400 mg", standard_params=None):
    """Generate a PDF compliance report from JSON data using reportlab."""
    # Load JSON data
    with open(json_path, 'r', encoding='utf-8') as json_file:
        data = json.load(json_file)

    if isinstance(data, list):
        compliance_entries = []
        total_entries = 0
        for item in data:
            if 'compliance' in item:
                compliance_entries.extend(item['compliance'])
                total_entries += len(item['compliance'])
        logger.info(f"Loaded JSON data from: {json_path}, {total_entries} entries (from {len(data)} chunks)")
    else:
        compliance_entries = data.get('compliance', [])
        total_entries = len(compliance_entries)
        logger.info(f"Loaded JSON data from: {json_path}, {total_entries} entries")

    # Set up PDF document
    doc = SimpleDocTemplate(pdf_output, pagesize=A4, leftMargin=0.5*inch, rightMargin=0.5*inch, topMargin=0.5*inch, bottomMargin=0.5*inch)
    elements = []

    # Define styles
    styles = getSampleStyleSheet()
    title_style = styles['Title']
    heading_style = styles['Heading2']
    normal_style = ParagraphStyle(name='NormalWrap', parent=styles['Normal'], wordWrap='CJK', fontSize=8, leading=10)
    footer_style = ParagraphStyle(name='Footer', parent=styles['Normal'], fontSize=8, alignment=1, spaceBefore=10)

    # Add title and introduction
    elements.append(Paragraph("Compliance Report", title_style))
    elements.append(Spacer(1, 0.2*inch))
    elements.append(Paragraph(f"Batch Compliance Report for {product_name}", heading_style))
    elements.append(Spacer(1, 0.1*inch))

    # Add standard parameters section if provided
    if standard_params:
        elements.append(Paragraph("Standard Parameters", heading_style))
        elements.append(Spacer(1, 0.05*inch))
        for param, value in standard_params.items():
            elements.append(Paragraph(f"{param}: {value}", normal_style))
        elements.append(Spacer(1, 0.2*inch))

    # Add introduction to compliance table
    intro_text = ("This document presents the compliance analysis for the batch manufacturing record (BMR). "
                  "The table below compares the actual values recorded during the manufacturing process against "
                  "the expected values specified in the master BMR.")
    elements.append(Paragraph(intro_text, normal_style))
    elements.append(Spacer(1, 0.2*inch))
    elements.append(Paragraph("Compliance Details", heading_style))
    elements.append(Paragraph("The following table summarizes the compliance status for key parameters:", normal_style))
    elements.append(Spacer(1, 0.1*inch))

    # Prepare table data
    table_data = [["Parameter", "Actual Value", "Expected Value", "Compliant", "Explanation"]]
    compliant_values = []  # Store compliant column values to determine colors
    for entry in compliance_entries:
        # If expected value is "non stated", set Compliant to "--"
        if entry['expected_value'].lower() == "non stated":
            compliant_text = "--"
        else:
            compliant_text = "Yes" if entry['is_compliant'] else "No"
        
        compliant_values.append(compliant_text)  # Store for coloring
        
        row = [
            wrap_text(entry['parameter'], 80, normal_style),
            wrap_text(entry['actual_value'], 100, normal_style),
            wrap_text(entry['expected_value'], 100, normal_style),
            compliant_text,
            wrap_text(entry['explanation'], 150, normal_style)
        ]
        table_data.append(row)

    # Define column widths
    col_widths = [100, 120, 120, 60, 180]

    # Create the table with basic styles
    table = Table(table_data, colWidths=col_widths, repeatRows=1)
    table_styles = [
        ('BACKGROUND', (0, 0), (-1, 0), colors.lightgrey),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.black),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, 0), 8),
        ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('FONTNAME', (0, 1), (-1, -1), 'Helvetica'),
        ('FONTSIZE', (0, 1), (-1, -1), 8),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.black),
        ('LEFTPADDING', (0, 0), (-1, -1), 4),
        ('RIGHTPADDING', (0, 0), (-1, -1), 4),
        ('TOPPADDING', (0, 0), (-1, -1), 4),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
    ]

    # Apply TEXTCOLOR to the Compliant column (column 3) based on values
    for row_idx, value in enumerate(compliant_values, start=1):  # Start at row 1 (skip header)
        if value == "Yes":
            table_styles.append(('TEXTCOLOR', (3, row_idx), (3, row_idx), colors.green))
        elif value == "No":
            table_styles.append(('TEXTCOLOR', (3, row_idx), (3, row_idx), colors.red))
        elif value == "--":
            table_styles.append(('TEXTCOLOR', (3, row_idx), (3, row_idx), colors.black))

    # Apply the styles to the table
    table.setStyle(TableStyle(table_styles))
    elements.append(table)

    # Add footer
    elements.append(Spacer(1, 0.5*inch))
    footer_text = "Generated by Frobe AI"
    elements.append(Paragraph(footer_text, footer_style))

    # Build the PDF
    doc.build(elements)
    logger.info(f"PDF generated successfully: {pdf_output}")
    

def generate_non_compliant_pdf(json_path, pdf_output="non_compliance_report.pdf", product_name="Cefixime Tablets USP 400 mg", standard_params=None):
    """Generate a PDF compliance report from JSON data showing only non-compliant entries using reportlab."""
    # Load JSON data
    with open(json_path, 'r', encoding='utf-8') as json_file:
        data = json.load(json_file)

    if isinstance(data, list):
        compliance_entries = []
        total_entries = 0
        for item in data:
            if 'compliance' in item:
                compliance_entries.extend(item['compliance'])
                total_entries += len(item['compliance'])
        logger.info(f"Loaded JSON data from: {json_path}, {total_entries} entries (from {len(data)} chunks)")
    else:
        compliance_entries = data.get('compliance', [])
        total_entries = len(compliance_entries)
        logger.info(f"Loaded JSON data from: {json_path}, {total_entries} entries")

    # Filter only non-compliant entries
    non_compliant_entries = [entry for entry in compliance_entries if not entry['is_compliant']]
    logger.info(f"Found {len(non_compliant_entries)} non-compliant entries out of {total_entries} total entries")

    # Set up PDF document
    doc = SimpleDocTemplate(pdf_output, pagesize=A4, leftMargin=0.5*inch, rightMargin=0.5*inch, topMargin=0.5*inch, bottomMargin=0.5*inch)
    elements = []

    # Define styles
    styles = getSampleStyleSheet()
    title_style = styles['Title']
    heading_style = styles['Heading2']
    normal_style = ParagraphStyle(name='NormalWrap', parent=styles['Normal'], wordWrap='CJK', fontSize=8, leading=10)
    footer_style = ParagraphStyle(name='Footer', parent=styles['Normal'], fontSize=8, alignment=1, spaceBefore=10)

    # Add title and introduction
    elements.append(Paragraph("Compliance Report Summary", title_style))
    elements.append(Spacer(1, 0.2*inch))
    elements.append(Paragraph(f"Batch Compliance Report Summary for {product_name}", heading_style))
    elements.append(Spacer(1, 0.1*inch))

    # Add standard parameters section if provided
    if standard_params:
        elements.append(Paragraph("Standard Parameters", heading_style))
        elements.append(Spacer(1, 0.05*inch))
        for param, value in standard_params.items():
            elements.append(Paragraph(f"{param}: {value}", normal_style))
        elements.append(Spacer(1, 0.2*inch))

    # Add introduction to compliance table
    intro_text = ("This document presents the compliance analysis for the batch manufacturing record (BMR). "
                  "The table below compares the actual values recorded during the manufacturing process against "
                  "the expected values specified in the master BMR.")
    elements.append(Paragraph(intro_text, normal_style))
    elements.append(Spacer(1, 0.2*inch))
    elements.append(Paragraph("Compliance Details", heading_style))
    elements.append(Paragraph("The following table summarizes the compliance status for key parameters:", normal_style))
    elements.append(Paragraph("All parameters are complied with except the below:", normal_style))
    elements.append(Spacer(1, 0.1*inch))

    # Check if there are any non-compliant entries
    if not non_compliant_entries:
        elements.append(Paragraph("No non-compliant parameters found. All parameters are compliant.", normal_style))
    else:
        # Prepare table data for non-compliant entries only
        table_data = [["Parameter", "Actual Value", "Expected Value", "Compliant", "Explanation"]]
        compliant_values = []  # Store compliant column values to determine colors
        
        for entry in non_compliant_entries:
            # If expected value is "non stated", set Compliant to "--"
            if entry['expected_value'].lower() == "non stated":
                compliant_text = "--"
            else:
                compliant_text = "Yes" if entry['is_compliant'] else "No"
            
            compliant_values.append(compliant_text)  # Store for coloring
            
            row = [
                wrap_text(entry['parameter'], 80, normal_style),
                wrap_text(entry['actual_value'], 100, normal_style),
                wrap_text(entry['expected_value'], 100, normal_style),
                compliant_text,
                wrap_text(entry['explanation'], 150, normal_style)
            ]
            table_data.append(row)

        # Define column widths
        col_widths = [100, 120, 120, 60, 180]

        # Create the table with basic styles
        table = Table(table_data, colWidths=col_widths, repeatRows=1)
        table_styles = [
            ('BACKGROUND', (0, 0), (-1, 0), colors.lightgrey),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.black),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 8),
            ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ('FONTNAME', (0, 1), (-1, -1), 'Helvetica'),
            ('FONTSIZE', (0, 1), (-1, -1), 8),
            ('GRID', (0, 0), (-1, -1), 0.5, colors.black),
            ('LEFTPADDING', (0, 0), (-1, -1), 4),
            ('RIGHTPADDING', (0, 0), (-1, -1), 4),
            ('TOPPADING', (0, 0), (-1, -1), 4),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
        ]

        # Apply TEXTCOLOR to the Compliant column (column 3) based on values
        for row_idx, value in enumerate(compliant_values, start=1):  # Start at row 1 (skip header)
            if value == "Yes":
                table_styles.append(('TEXTCOLOR', (3, row_idx), (3, row_idx), colors.green))
            elif value == "No":
                table_styles.append(('TEXTCOLOR', (3, row_idx), (3, row_idx), colors.red))
            elif value == "--":
                table_styles.append(('TEXTCOLOR', (3, row_idx), (3, row_idx), colors.black))

        # Apply the styles to the table
        table.setStyle(TableStyle(table_styles))
        elements.append(table)

    # Add footer
    elements.append(Spacer(1, 0.5*inch))
    footer_text = "Generated by Frobe AI"
    elements.append(Paragraph(footer_text, footer_style))

    # Build the PDF
    doc.build(elements)
    logger.info(f"Non-compliant PDF generated successfully: {pdf_output}")
    logger.info(f"Total non-compliant entries included: {len(non_compliant_entries)}")

if __name__ == "__main__":
    json_path = "compliance_results.json"
    generate_pdf(json_path)  # Generate the normal compliance PDF
    generate_non_compliant_pdf(json_path)  # Generate the non-compliant PDF