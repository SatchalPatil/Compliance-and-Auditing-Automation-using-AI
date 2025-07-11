import faiss
import pickle
import google.generativeai as genai
import json
import logging
from chunking import read_bmr_file, chunk_bmr
from compliance_agent import set_index_and_metadata, extract_parameters_to_verify, retrieve_from_knowledge_base, analyze_compliance

# Constants
MASTER_INDEX_FILE = r"Path to Master_BMR_2_faiss.index"
MASTER_METADATA_FILE = r"Path to Master_BMR_2_metadata.pkl"
API_KEY = "GEMINI-API-KEY"
OUTPUT_JSON_PATH = "compliance_results.json"
OUTPUT_PDF_PATH = "compliance_report.pdf"
TEMP_EXTRACTED_PATH = "temp_extracted.txt"
TEMP_CLEANED_PATH = "temp_cleaned.txt"

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Load FAISS index and metadata once at startup
try:
    index = faiss.read_index(MASTER_INDEX_FILE)
    with open(MASTER_METADATA_FILE, 'rb') as file:
        metadata = pickle.load(file)
    set_index_and_metadata(index, metadata)
    logger.info("Loaded FAISS index and metadata successfully.")
except Exception as e:
    logger.error(f"Error loading FAISS index or metadata: {e}")
    raise

genai.configure(api_key=API_KEY)

def process_chunk(chunk: str, api_key: str) -> dict:
    """Process a single chunk through extraction, retrieval, and compliance check."""
    try:
        logger.info("=== Processing Chunk ===")
        
        # Extract parameters
        parameters = extract_parameters_to_verify(chunk, api_key)
        if not parameters:
            logger.warning("Failed to extract parameters")
            return {"compliance": [{
                "parameter": "non stated",
                "actual_value": "non stated",
                "expected_value": "non stated",
                "is_compliant": False,
                "explanation": "No parameters extracted from input chunk"
            }], "standard_params": {}}
       
        # Create query from parameters
        query = ", ".join([f"{p['name']}: {p['value']}" for p in parameters])
        retrieved_chunks = retrieve_from_knowledge_base(query, api_key, k=5)
        if not retrieved_chunks:
            logger.warning("Failed to retrieve standard parameters")
            standard_params = [{"name": "non stated", "value": "non stated", "context": "non stated"}]
        else:
            standard_params = retrieved_chunks[0].get('parameters', [])
            if not standard_params or not isinstance(standard_params, list):
                logger.warning("No valid parameters found in retrieved chunk")
                standard_params = [{"name": "non stated", "value": "non stated", "context": "non stated"}]
        
        # Compliance check
        compliance_result, standard_params = analyze_compliance(parameters, retrieved_chunks or [{}], api_key)
        if not compliance_result:
            logger.warning("Compliance check failed, using default compliance result")
            compliance_result = [{
                "parameter": "non stated",
                "actual_value": "non stated",
                "expected_value": "non stated",
                "is_compliant": False,
                "explanation": "No compliance data available due to analysis failure"
            }]
        
        return {"compliance": compliance_result, "standard_params": standard_params}
    
    except Exception as e:
        logger.error(f"Error processing chunk: {e}")
        return {"compliance": [{
            "parameter": "non stated",
            "actual_value": "non stated",
            "expected_value": "non stated",
            "is_compliant": False,
            "explanation": f"Error processing chunk: {str(e)}"
        }], "standard_params": {}}
