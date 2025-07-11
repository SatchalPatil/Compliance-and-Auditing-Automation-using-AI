#!/usr/bin/env python3
import sys
import re
import logging
from collections import OrderedDict
import pdfplumber

# Configure Logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s"
)
logger = logging.getLogger(__name__)

# Utility Functions
def clean_text(txt):
    if not txt:
        return ""
    txt = re.sub(r"_+", "", txt)
    return re.sub(r"\s+", " ", txt.strip())

def is_key_value(table):
    rows = [row for row in table if any(cell for cell in row)]
    return all(len([c for c in row if c and c.strip()]) == 2 for row in rows)

def is_matrix(table):
    if len(table) < 2:
        return False
    header = table[0]
    if sum(1 for c in header if c and c.strip()) < 3:
        return False
    target = len(header)
    count = sum(1 for row in table[1:] if len(row) == target)
    return (count / max(1, len(table)-1)) >= 0.7

def extract_pairs(table):
    pairs = []
    for row in table:
        cells = [clean_text(c) for c in row]
        if len(cells) == 2 and all(cells):
            pairs.append(tuple(cells))
    return pairs

def extract_matrix(table):
    headers = [clean_text(h) or f"Col_{i}" for i,h in enumerate(table[0])]
    rows = []
    for row in table[1:]:
        cleaned = [clean_text(c) for c in row]
        if any(cleaned):
            cleaned = (cleaned + [""]*len(headers))[:len(headers)]
            rows.append(cleaned)
    return headers, rows

def format_key_value(pairs):
    bullets = []
    for k, v in pairs:
        kl = k.lower()
        if "label claim" in kl:
            bullets.append(f"- Label Claim:")
            m1 = re.search(r'export\s*:\s*(.+?)(?=domestic|$)', v, re.IGNORECASE)
            m2 = re.search(r'domestic\s*:\s*(.+)', v, re.IGNORECASE)
            if m1:
                bullets.append(f"    • Export: {clean_text(m1.group(1))}")
            if m2:
                bullets.append(f"    • Domestic: {clean_text(m2.group(1))}")
        else:
            bullets.append(f"- {k}: {v}")
    return bullets

def format_matrix(headers, rows):
    bullets = [f"- {hdr}" for hdr in headers]
    for row in rows:
        main = row[0]
        bullets.append(f"- {main}:")
        for hdr, cell in zip(headers[1:], row[1:]):
            if cell:
                bullets.append(f"    • {hdr}: {cell}")
    return bullets

def format_irregular(table):
    bullets = []
    for row in table:
        segs = [clean_text(c) for c in row if c and c.strip()]
        if segs:
            bullets.append(f"- {' | '.join(segs)}")
    return bullets

# Extraction Logic
def extract_with_pdfplumber(page):
    settings = [
        {"vertical_strategy":"lines_strict","horizontal_strategy":"lines_strict"},
        {"vertical_strategy":"lines","horizontal_strategy":"text"}
    ]
    for s in settings:
        tbls = page.extract_tables(table_settings=s)
        if tbls:
            return tbls
    return []

def process_page(pdf_path, page, page_no, output):
    tables = extract_with_pdfplumber(page)
    output.append(f"Page {page_no}:")
    if not tables:
        output.append("- (No tables found)")
        output.append("")
        return
    for tbl in tables:
        table = [r for r in tbl if any(r)]
        if is_key_value(table):
            pairs = extract_pairs(table)
            output += format_key_value(pairs)
        elif is_matrix(table):
            headers, rows = extract_matrix(table)
            output += format_matrix(headers, rows)
        else:
            output += format_irregular(table)
    output.append("")

def extract_pdf_to_text(pdf_path, out_path=None):
    """Extract text from PDF and return it, optionally saving to out_path."""
    output = []
    with pdfplumber.open(pdf_path) as pdf:
        for i, page in enumerate(pdf.pages, start=1):
            process_page(pdf_path, page, i, output)
    text_content = "\n".join(output)
    if out_path:
        with open(out_path, "w", encoding="utf-8") as f:
            f.write(text_content)
        logger.info(f"Extraction complete. Saved to {out_path}")
    return text_content

def main(pdf_path, out_path):
    extract_pdf_to_text(pdf_path, out_path)

if __name__ == "__main__":
    if len(sys.argv) != 3:
        print("Usage: python pdfconv.py <input.pdf> <output.txt>")
        sys.exit(1)
    main(sys.argv[1], sys.argv[2])