from flask import Flask, render_template, request, send_file
from imposition import Imposer
from pypdf import PdfReader
import io

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
        imposer = Imposer(file.stream, n_up)
        output_pdf = imposer.generate()
        
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
        reader = PdfReader(file.stream)
        count = len(reader.pages)
        return {'pages': count}
    except Exception as e:
        return {'error': str(e)}, 500

if __name__ == '__main__':
    app.run(debug=True, port=8000)
