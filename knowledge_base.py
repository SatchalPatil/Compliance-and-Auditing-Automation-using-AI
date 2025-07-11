import os
import hashlib
import time
import pickle
import numpy as np
import faiss
import google.generativeai as genai
from langchain.text_splitter import RecursiveCharacterTextSplitter

# Chunking Configuration
CHUNK_SIZE = 300
CHUNK_OVERLAP = 50

# Gemini API Configuration
GEMINI_MODEL = 'models/text-embedding-004'  # Using the latest, high-performance model
BATCH_SIZE = 100  # Gemini API has a limit of 100 texts per batch

# --- 2. Setup Gemini API ---
api_key_str = "AIzaSyC9-vR_8Ss0Cs6u282G6iGPN2N2bm8GsPU"

# Set the API key for the genai library
os.environ["GOOGLE_API_KEY"] = api_key_str
genai.configure(api_key=os.environ["GOOGLE_API_KEY"])

print(f"Gemini API configured using model: {GEMINI_MODEL}")

# --- 3. Hardcoded Input File Path ---
INPUT_FILE_PATH = "Master_BMR_2.txt"

# --- 4. Helper Functions ---

def read_text_from_file(file_path):
    """Reads and returns the content of a text file, handling potential errors."""
    try:
        with open(file_path, 'r', encoding='utf-8') as file:
            return file.read()
    except FileNotFoundError:
        print(f"Error: The file '{file_path}' was not found.")
        return None
    except Exception as e:
        print(f"An error occurred while reading the file: {e}")
        return None

def generate_chunk_id(content):
    """Generates a unique MD5 hash ID for a chunk of text."""
    return hashlib.md5(content.encode('utf-8')).hexdigest()

def embed_with_retry(model, content, task_type, max_retries=3):
    """Embeds content using Gemini API with an exponential backoff retry mechanism."""
    for attempt in range(max_retries):
        try:
            return genai.embed_content(model=model, content=content, task_type=task_type)
        except Exception as e:
            print(f"API call failed (attempt {attempt + 1}/{max_retries}): {e}")
            if attempt < max_retries - 1:
                time.sleep(2 ** attempt)  # Wait 1, 2, 4 seconds...
            else:
                print("API call failed after multiple retries. Exiting.")
                raise

# --- 5. Main Creation Logic ---

def create_database():
    """Main function to create the FAISS database from the input text file."""
    input_filepath = INPUT_FILE_PATH
    print(f"\nProcessing file: {input_filepath}")

    # Step 1: Load and Chunk the Document
    raw_text = read_text_from_file(input_filepath)
    if raw_text is None:
        return  # Exit if file could not be read

    print("Text loaded successfully.")

    text_splitter = RecursiveCharacterTextSplitter(
        chunk_size=CHUNK_SIZE,
        chunk_overlap=CHUNK_OVERLAP,
        length_function=lambda x: len(x.split())  # Splits based on word count
    )
    chunks_text = text_splitter.split_text(raw_text)
    
    if not chunks_text:
        print("No text chunks were generated. The input file might be empty or too short.")
        return
        
    print(f"Split document into {len(chunks_text)} chunks.")

    # Step 2: Prepare Chunks and Metadata
    all_metadata = []
    for i, chunk in enumerate(chunks_text):
        meta = {
            "source": os.path.basename(input_filepath),
            "chunk_id": generate_chunk_id(chunk),
            "chunk_index": i,
            "text": chunk  # Store the actual text in metadata for later retrieval
        }
        all_metadata.append(meta)

    # Step 3: Generate Embeddings using Gemini API (with batching)
    print(f"\nGenerating embeddings for {len(chunks_text)} chunks...")
    all_embeddings = []
    
    for i in range(0, len(chunks_text), BATCH_SIZE):
        batch_chunks = chunks_text[i:i + BATCH_SIZE]
        response = embed_with_retry(
            model=GEMINI_MODEL,
            content=batch_chunks,
            task_type="RETRIEVAL_DOCUMENT"
        )
        all_embeddings.extend(response['embedding'])
        print(f"  ... Embedded {len(all_embeddings)}/{len(chunks_text)} chunks")

    embeddings_np = np.array(all_embeddings).astype('float32')
    print("Embeddings generated successfully.")

    # Step 4: Create and Save FAISS Index
    dimension = embeddings_np.shape[1]
    index = faiss.IndexFlatL2(dimension)
    index.add(embeddings_np)

    # Generate output filenames
    base_filename = os.path.splitext(os.path.basename(input_filepath))[0]
    index_file = f"{base_filename}_faiss.index"
    metadata_file = f"{base_filename}_metadata.pkl"
    
    faiss.write_index(index, index_file)
    print(f"\nFAISS index created with {index.ntotal} vectors of dimension {dimension}.")
    print(f"Index saved to: {index_file}")

    # Step 5: Save Metadata
    with open(metadata_file, 'wb') as f:
        pickle.dump(all_metadata, f)
    print(f"Metadata saved to: {metadata_file}")

    print("\nDatabase creation process complete!")

if __name__ == "__main__":
    create_database()