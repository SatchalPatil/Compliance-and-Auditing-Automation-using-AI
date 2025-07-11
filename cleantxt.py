#!/usr/bin/env python3
import sys
import re
import logging

# Configure Logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s"
)
logger = logging.getLogger(__name__)

def clean_text_file(input_path, output_path):
    """Clean text file by extracting key-value pairs and reformatting."""
    try:
        cleaned_lines = []
        current_record = {}

        with open(input_path, 'r', encoding='utf-8') as f:
            lines = f.readlines()

        for line in lines:
            line = line.strip()
            
            if not line:
                continue

            # Detect record start: e.g. "- 16:" or "- 4:"
            if re.match(r"^- \d+:$", line):
                if current_record:
                    # Flush previous record
                    for key, val in current_record.items():
                        cleaned_lines.append(f"{key}: {val}")
                    cleaned_lines.append("")  # Blank line between records
                    current_record = {}
                continue  # Skip the index line

            # Key-Value pattern: e.g. "• Ingredient: Hypromellose"
            match = re.match(r"•\s*(.*?):\s*(.*)", line)
            if match:
                key, value = match.groups()
                key = key.strip()
                value = value.strip()
                current_record[key] = value
                continue

            # Inline key-value e.g. "- Ingredient"
            match = re.match(r"^- (.*)", line)
            if match:
                key = match.group(1).strip()
                current_record[key] = ""  # Mark as key awaiting value (if needed)
                continue

            # Handle possible continuation lines
            if current_record and line.startswith("•"):
                # Example: "• Std Qty / batch: 0.30"
                match = re.match(r"•\s*(.*?):\s*(.*)", line)
                if match:
                    key, value = match.groups()
                    current_record[key.strip()] = value.strip()
        
        # Flush last record
        if current_record:
            for key, val in current_record.items():
                cleaned_lines.append(f"{key}: {val}")
            cleaned_lines.append("")

        # Write output
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write('\n'.join(cleaned_lines))

        logger.info(f"Cleaned file written to: {output_path}")
    
    except Exception as e:
        logger.error(f"Error cleaning text file: {e}")
        raise

if __name__ == "__main__":
    if len(sys.argv) != 3:
        print("Usage: python cleantxt.py <input.txt> <output.txt>")
        sys.exit(1)
    clean_text_file(sys.argv[1], sys.argv[2])