from flask import Flask, render_template, request, send_file
from imposition import Imposer
from pypdf import PdfReader
import io
import threading

# LIMITS
MAX_QUEUE_SIZE = 8
MAX_FILE_SIZE = 60 * 1024 * 1024  # 60 MB

# Semaphore for the Queue (Waiting Room)
# We use non-blocking acquire to reject users when full
queue_semaphore = threading.BoundedSemaphore(value=MAX_QUEUE_SIZE)

# Lock for the Processing (The Chair)
processing_lock = threading.Lock()

app = Flask(__name__)

@app.route('/', methods=['GET'])
def index():
    return render_template('index.html')

@app.route('/about')
def about():
    return render_template('about.html')

@app.route('/contact')
def contact():
    return render_template('contact.html')

@app.route('/privacy')
def privacy():
    return render_template('privacy.html')

@app.route('/robots.txt')
def robots():
    return send_file('static/robots.txt')

@app.route('/sitemap.xml')
def sitemap():
    return send_file('static/sitemap.xml')

@app.route('/process', methods=['POST'])
def process():
    if 'pdf_file' not in request.files:
        return 'No file uploaded', 400
    
    file = request.files['pdf_file']
    if file.filename == '':
        return 'No file selected', 400
        
    try:
        n_up = int(request.form.get('n_up', 2))
    except ValueError:
        n_up = 2
        
    # Process the file
    try:
        # 1. Check File Size (Content-Length)
        if request.content_length and request.content_length > MAX_FILE_SIZE:
             return f"File too large. Maximum size is {MAX_FILE_SIZE // (1024*1024)}MB.", 413

        # 2. Try to Enter Queue
        # acquire(blocking=False) returns False if queue is full
        if not queue_semaphore.acquire(blocking=False):
             return "Server is currently full. Please wait a moment and try again.", 503

        try:
            # 3. entered queue, now wait for processing lock
            with processing_lock:
                 # Check actual file size again
                file.seek(0, 2) # Seek to end
                size = file.tell()
                file.seek(0) # Reset
                
                if size > MAX_FILE_SIZE:
                    return f"File too large. Maximum size is {MAX_FILE_SIZE // (1024*1024)}MB.", 413

                # Process
                imposer = Imposer(file.stream, n_up)
                output_pdf = imposer.generate()
        finally:
            # Always release the queue spot
            queue_semaphore.release()
        
        return send_file(
            output_pdf,
            as_attachment=True,
            download_name=f'imposed_{n_up}up_{file.filename}',
            mimetype='application/pdf'
        )
    except Exception as e:
        app.logger.error(f"Error processing PDF: {e}")
        return f"Error processing PDF: {str(e)}", 500

@app.route('/count-pages', methods=['POST'])
def count_pages():
    if 'pdf_file' not in request.files:
        return {'error': 'No file uploaded'}, 400
    
    file = request.files['pdf_file']
    if file.filename == '':
        return {'error': 'No file selected'}, 400
        
    try:
        if not queue_semaphore.acquire(blocking=False):
             return {'error': 'Server is currently full. Please wait a moment.'}, 503

        try:
             with processing_lock:
                reader = PdfReader(file.stream)
                count = len(reader.pages)
        finally:
             queue_semaphore.release()

        return {'pages': count}
    except Exception as e:
        return {'error': str(e)}, 500

if __name__ == '__main__':
    app.run(debug=True, port=8000)
