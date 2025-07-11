import threading
import time
import numpy as np
import google.generativeai as genai
import json
import logging
from typing import List, Dict, Any
import re

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Global variables for FAISS index and metadata
index = None
metadata = None
api_semaphore = threading.Semaphore(1)

def set_index_and_metadata(idx, meta):
    """Set the global FAISS index and metadata."""
    global index, metadata
    index = idx
    metadata = meta
    logger.info("FAISS index and metadata set successfully.")

def extract_parameters_to_verify(chunk: str, api_key: str) -> List[Dict[str, Any]]:
    """Extract parameters that need to be verified from the content."""
    logger.info(f"\n=== Extracting Parameters to Verify ===")
    logger.info(f"Input content length: {len(chunk)} characters")
    
    with api_semaphore:
        try:
            genai.configure(api_key=api_key)
            model = genai.GenerativeModel('gemini-2.0-flash')
            system_prompt = """You are a BMR compliance expert. Extract parameters that need to be verified for compliance.
            Look for parameters in these categories:
            1. Product Information (name, label claims, batch details)
            2. Manufacturing Details (batch size, location, signatures)
            3. General Specifications (dosage form, shelf life, storage)
            4. Process Parameters (temperatures, pressures, speeds)
            5. Quality Parameters (yields, weights, dimensions)
            6. Material Specifications (ingredients, quantities)
            7. Equipment Parameters (settings, conditions)
            8. Packaging Parameters (specifications, requirements)
            DO NOT EXTRACT PARAMETERS LIKE "Prepared By QA" OR "Reviewed By Production" OR "Approved By QA"
            
            For each parameter, extract:
            - name: parameter name
            - value: parameter value
            - context: section or category it belongs to
            
            Return a JSON array of parameter objects with this structure:
            [
                {
                    "name": string,
                    "value": string,
                    "context": string
                }
            ]
            
            Do not include any other text or explanation outside the JSON array."""
            
            prompt = (
                f"Extract parameters from this content that need compliance verification:\n"
                f"{chunk}\n\n"
                f"Return ONLY a valid JSON array of parameter objects. Do not include any other text."
            )
            
            response = model.generate_content([system_prompt, prompt])
            text = response.text.strip()
            logger.debug(f"Raw Gemini response: {text}")
            
            # Extract JSON array
            start = text.find('[')
            end = text.rfind(']') + 1
            if start >= 0 and end > start:
                json_text = text[start:end]
            else:
                raise ValueError("No JSON array found in response")
            
            parameters = json.loads(json_text)
            
            # Validate structure
            if not isinstance(parameters, list):
                raise ValueError("Response is not a JSON array")
            for param in parameters:
                if not isinstance(param, dict):
                    raise ValueError("Parameter is not a JSON object")
                if not all(key in param for key in ["name", "value", "context"]):
                    raise ValueError("Parameter missing required fields")
                if not all(isinstance(param[key], str) for key in ["name", "value", "context"]):
                    raise ValueError("Parameter fields must be strings")
            
            logger.info(f"Successfully extracted {len(parameters)} parameters")
            for param in parameters:
                logger.info(f"Parameter: {param['name']} = {param['value']} (Context: {param['context']})")
            
            time.sleep(2)  #Delay
            return parameters
            
        except Exception as e:
            logger.error(f"Error extracting parameters: {e}")
            return []

def retrieve_from_knowledge_base(query: str, api_key: str, k: int = 5) -> List[Dict[str, Any]]:
    """Retrieve relevant chunks from the knowledge base using FAISS."""
    with api_semaphore:
        try:
            genai.configure(api_key=api_key)
            embedding = genai.embed_content(
                model="models/text-embedding-004",
                content=query,
                task_type="RETRIEVAL_QUERY"
            )["embedding"]
            query_vector = np.array([embedding]).astype('float32')
            
            # Search the index
            distances, indices = index.search(query_vector, k)
            
            # Get the chunks
            chunks = []
            for distance, idx in zip(distances[0], indices[0]):
                if idx != -1:
                    chunk = metadata[idx].copy()
                    chunk['similarity_score'] = float(distance)
                    chunks.append(chunk)
            
            # Log the number of chunks found
            logger.info(f"Found {len(chunks)} relevant chunks for query: {query[:100]}...")
            
            # Log each chunk with its score and preview
            for i, chunk in enumerate(chunks, 1):
                preview = chunk.get('text', '')[:100] + '...'
                logger.info(f"Chunk {i}: Score: {chunk['similarity_score']:.4f}, Text preview: {preview}")
            
            # Filter chunks with high L2 distance
            filtered_chunks = [chunk for chunk in chunks if chunk['similarity_score'] < 0.8]
            
            if not filtered_chunks:
                logger.warning(f"No sufficiently relevant chunks found for query: {query[:100]}...")
                return []
            
            time.sleep(2)  #Delay 
            return filtered_chunks
        
        except Exception as e:
            logger.error(f"Error retrieving from knowledge base: {e}")
            return []

def analyze_compliance(parameters: List[Dict[str, Any]], master_chunks: List[Dict[str, Any]], api_key: str) -> List[Dict[str, Any]]:
    """Analyze compliance of parameters against master BMR requirements."""
    with api_semaphore:
        try:
            genai.configure(api_key=api_key)
            model = genai.GenerativeModel('gemini-2.0-flash')
            
            # Prepare master BMR content
            master_content = "\n".join([chunk.get("text", "") for chunk in master_chunks])
            
            system_prompt = """You are a compliance analysis expert. Your task is to analyze each parameter's compliance with the master BMR requirements.
            For each parameter:
            1. Compare the actual value against the expected value from master BMR
            2. Determine if the parameter is compliant
            3. Provide a clear explanation for the compliance decision
            4. If non-compliant, explain what needs to be changed to achieve compliance
            
            Format your response as a JSON array of parameter analyses, where each analysis contains:
            {
                "parameter": string,
                "actual_value": string,
                "expected_value": string,
                "is_compliant": boolean,
                "explanation": string
            }
            
            IMPORTANT: 
            - Return ONLY the JSON array, no other text
            - Use true/false for is_compliant (not strings)
            - If any values are missing, set them to "non stated"
            - Ensure all JSON is properly formatted with correct delimiters
            """
            
            prompt = (
                f"Analyze the compliance of these parameters with the master BMR requirements:\n\n"
                f"Parameters to analyze:\n{json.dumps(parameters, indent=2)}\n\n"
                f"Master BMR content for reference:\n{master_content}\n\n"
                f"Return a JSON array of parameter analyses. Each analysis must include parameter, actual_value, "
                f"expected_value, is_compliant, and explanation fields."
            )
            
            response = model.generate_content([system_prompt, prompt])
            text = response.text.strip()
            logger.debug(f"Raw Gemini response: {text}")
            
            # Extract JSON array
            start = text.find('[')
            end = text.rfind(']') + 1
            if start >= 0 and end > start:
                json_text = text[start:end]
            else:
                raise ValueError("No JSON array found in response")
                
            # Clean JSON
            json_text = json_text.replace('\n', ' ').replace('\r', '')
            json_text = re.sub(r',\s*}', '}', json_text)
            json_text = re.sub(r',\s*]', ']', json_text)
            
            result = json.loads(json_text)
            
            # Validate and clean results
            if not isinstance(result, list):
                raise ValueError("Response is not a JSON array")
            
            cleaned_result = []
            for param in result:
                cleaned_param = {
                    "parameter": param.get("parameter", "non stated"),
                    "actual_value": param.get("actual_value", "non stated"),
                    "expected_value": param.get("expected_value", "non stated"),
                    "is_compliant": param.get("is_compliant", False),
                    "explanation": param.get("explanation", "No explanation provided")
                }
                if not isinstance(cleaned_param["is_compliant"], bool):
                    cleaned_param["is_compliant"] = cleaned_param["is_compliant"].lower() == "true"
                cleaned_result.append(cleaned_param)
            
            logger.info(f"Compliance analysis completed: {len(cleaned_result)} parameters analyzed")
            time.sleep(2)

            # Identify standard parameters
            system_prompt2 = """Parse and analyze this JSON response to identify standard parameters 
            (for example: 'MFR Reference No', 'BMR Reference No', 'Batch Number', all kinds of Dates, etc).
            
            Standard parameters include:
            - Any parameter containing "Reference No" in the name (e.g., 'MFR Reference No', 'BMR Reference No')
            - Any parameter named "Batch Number" or "Batch No."
            - Any parameter with "product name"
            - Any parameter with "Date" in the name or whose actual_value matches common date formats (e.g., 'DD/MM/YYYY', 'YYYY-MM-DD', 'DD-MM-YYYY')
            - DO NOT include measurable data (for ex: temperature and weight etc.)
            Format your response as a JSON object mapping standard parameter names to their actual values:
            {
                "parameter_name": "actual_value",
                ...
            }
            
            Return ONLY the JSON object, no other text."""
            
            prompt2 = (
                f"Identify standard parameters in the following JSON response:\n\n"
                f"Compliance analysis results:\n{json.dumps(cleaned_result, indent=2)}\n\n"
                f"Return a JSON object mapping standard parameter names to their actual values."
            )
            
            response2 = model.generate_content([system_prompt2, prompt2])
            text2 = response2.text.strip()
            logger.debug(f"Raw Gemini response for standard parameters: {text2}")
            
            # Extract JSON object
            start2 = text2.find('{')
            end2 = text2.rfind('}') + 1
            if start2 >= 0 and end2 > start2:
                json_text2 = text2[start2:end2]
            else:
                raise ValueError("No JSON object found in response for standard parameters")
            
            # Clean JSON
            json_text2 = json_text2.replace('\n', ' ').replace('\r', '')
            json_text2 = re.sub(r',\s*}', '}', json_text2)
            json_text2 = re.sub(r',\s*]', ']', json_text2)
            
            standard_params = json.loads(json_text2)
            
            # Validate standard_params
            if not isinstance(standard_params, dict):
                raise ValueError("standard_params is not a JSON object")
            for key, value in standard_params.items():
                if not isinstance(key, str) or not isinstance(value, str):
                    raise ValueError("standard_params keys and values must be strings")
            
            # Filter out standard parameters from cleaned_result
            filtered_results = [
                param for param in cleaned_result
                if param["parameter"] not in standard_params
            ]
            
            logger.info(f"Standard parameters identified: {len(standard_params)}")
            logger.info(f"Non-standard parameters remaining: {len(filtered_results)}")
            time.sleep(2)
            
            return filtered_results, standard_params
            
        except Exception as e:
            logger.error(f"Error in analyze_compliance: {e}")
            return [], {}