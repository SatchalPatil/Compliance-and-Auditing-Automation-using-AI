def read_bmr_file(file_path):
    """Read the content of a BMR text file."""
    try:
        with open(file_path, 'r', encoding='utf-8') as file:
            return file.read()
    except FileNotFoundError:
        print(f"Error: File '{file_path}' not found.")
        raise
    except Exception as e:
        print(f"Error reading file '{file_path}': {e}")
        raise

def chunk_bmr(content, lines_per_chunk=500):
    """Chunk the BMR content into segments of specified line count."""
    lines = content.splitlines()
    chunks = [lines[i:i + lines_per_chunk] for i in range(0, len(lines), lines_per_chunk)]
    return ['\n'.join(chunk) for chunk in chunks]