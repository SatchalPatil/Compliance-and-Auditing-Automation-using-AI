from flask import Flask, request, render_template, send_file, redirect, url_for, session
import os
from main import process_chunk, API_KEY, OUTPUT_JSON_PATH, OUTPUT_PDF_PATH, TEMP_EXTRACTED_PATH, TEMP_CLEANED_PATH
from pdfconv import extract_pdf_to_text
from cleantxt import clean_text_file
from chunking import read_bmr_file, chunk_bmr
import json
import logging
import time

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

app = Flask(__name__)
app.secret_key = 'your_secret_key'  # Required for session; replace with a secure key
UPLOAD_FOLDER = 'uploads'
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

# Ensure upload folder exists
if not os.path.exists(UPLOAD_FOLDER):
    os.makedirs(UPLOAD_FOLDER)

@app.route('/')
def index():
    return render_template('index.html', processing=False, error=None, results=None, standard_params=None, non_compliant_pdf=None)

@app.route('/upload', methods=['POST'])
def upload_file():
    try:
        if 'file' not in request.files:
            return render_template('index.html', error="No file part", processing=False)
        
        file = request.files['file']
        if file.filename == '':
            return render_template('index.html', error="No file selected", processing=False)
        
        if file and file.filename.endswith('.pdf'):
            # Save the uploaded file
            filepath = os.path.join(app.config['UPLOAD_FOLDER'], file.filename)
            file.save(filepath)
            logger.info(f"File saved to {filepath}")

            # Store file path in session for processing
            session['filepath'] = filepath
            return redirect(url_for('process_status'))

    except Exception as e:
        logger.error(f"Error during upload: {e}")
        return render_template('index.html', error=f"Error during upload: {str(e)}", processing=False)

@app.route('/process_status')
def process_status():
    if 'filepath' not in session:
        return redirect(url_for('index'))

    filepath = session['filepath']
    if not hasattr(process_status, 'processing'):
        process_status.processing = False
        process_status.results = None
        process_status.standard_params = None
        process_status.error = None

    if not process_status.processing:
        process_status.processing = True
        try:
            logger.info(f"Starting PDF processing for {filepath}")
            extract_pdf_to_text(filepath, TEMP_EXTRACTED_PATH)
            logger.info(f"Text extracted to {TEMP_EXTRACTED_PATH}")

            clean_text_file(TEMP_EXTRACTED_PATH, TEMP_CLEANED_PATH)
            logger.info(f"Text cleaned and saved to: {TEMP_CLEANED_PATH}")

            content = read_bmr_file(TEMP_CLEANED_PATH)
            chunks = chunk_bmr(content, lines_per_chunk=300)
            logger.info(f"Created {len(chunks)} chunks from cleaned text: {TEMP_CLEANED_PATH}")

            results = []
            all_standard_params = {}
            for i, chunk in enumerate(chunks):
                logger.info(f"\nProcessing chunk {i}")
                result = process_chunk(chunk, API_KEY)
                all_standard_params.update(result["standard_params"])
                results.append({"chunk_index": i, "compliance": result["compliance"]})

            with open(OUTPUT_JSON_PATH, 'w', encoding='utf-8') as f:
                json.dump(results, f, indent=2)
            logger.info(f"Results saved to {OUTPUT_JSON_PATH}")

            from pdf_gen import generate_pdf
            generate_pdf(OUTPUT_JSON_PATH, OUTPUT_PDF_PATH, standard_params=all_standard_params)

            logger.info(f"Final PDF report generated: {OUTPUT_PDF_PATH}")

            process_status.results = results
            process_status.standard_params = all_standard_params
            process_status.error = None
        except Exception as e:
            logger.error(f"Error processing file: {e}")
            process_status.error = f"Error processing file: {str(e)}"
        finally:
            for temp_file in [filepath, TEMP_EXTRACTED_PATH, TEMP_CLEANED_PATH]:
                if os.path.exists(temp_file):
                    os.remove(temp_file)
            logger.info("Temporary files cleaned up.")
            process_status.processing = False

    return render_template('index.html', 
                          processing=process_status.processing,
                          results=process_status.results,
                          standard_params=process_status.standard_params,
                          error=process_status.error)

@app.route('/summarize', methods=['POST'])
def summarize():
    if 'filepath' not in session or not hasattr(process_status, 'results') or not process_status.results:
        return redirect(url_for('index'))

    try:
        from pdf_gen import generate_non_compliant_pdf
        non_compliant_pdf_path = "non_compliance_report.pdf"
        generate_non_compliant_pdf(OUTPUT_JSON_PATH, non_compliant_pdf_path, standard_params=process_status.standard_params)
        logger.info(f"Non-compliant PDF generated: {non_compliant_pdf_path}")
        return render_template('index.html', 
                              processing=False,
                              results=process_status.results,
                              standard_params=process_status.standard_params,
                              error=None,
                              non_compliant_pdf=non_compliant_pdf_path)
    except Exception as e:
        logger.error(f"Error generating non-compliant PDF: {e}")
        return render_template('index.html', 
                              processing=False,
                              results=process_status.results,
                              standard_params=process_status.standard_params,
                              error=f"Error generating summary: {str(e)}")

@app.route('/download_pdf')
def download_pdf():
    return send_file(OUTPUT_PDF_PATH, as_attachment=True)

@app.route('/download_non_compliant_pdf')
def download_non_compliant_pdf():
    return send_file("non_compliance_report.pdf", as_attachment=True)

if __name__ == "__main__":
    app.run(debug=True, port=5000)