import os
import sys
import tempfile
import uuid
from flask import Flask, request, render_template, send_file, flash, redirect, url_for, jsonify

# Add parent directory to path to import huffman_compressor
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from huffman_compressor import HuffmanCompressor

app = Flask(__name__)
app.secret_key = 'huffman_secure_key_2024'

# Use system temp directory
TEMP_DIR = tempfile.gettempdir()

# Track files to clean up after response
files_to_cleanup = []

@app.after_request
def cleanup_temp_files(response):
    """Clean up temporary files after sending response."""
    global files_to_cleanup
    for filepath in files_to_cleanup:
        try:
            if os.path.exists(filepath):
                os.remove(filepath)
        except Exception as e:
            print(f"Warning: Could not delete {filepath}: {e}")
    files_to_cleanup = []
    return response

@app.route('/', methods=['GET'])
def index():
    """Render the main web interface."""
    return render_template('index.html')

@app.route('/compress', methods=['POST'])
def compress():
    """Handle file compression requests."""
    global files_to_cleanup
    
    if 'file' not in request.files:
        flash('No file uploaded.', 'error')
        return redirect(url_for('index'))
    
    file = request.files['file']
    if file.filename == '':
        flash('No file selected.', 'error')
        return redirect(url_for('index'))
        
    try:
        # Define paths with unique temporary names during processing
        temp_id = str(uuid.uuid4())[:8]
        input_path = os.path.join(TEMP_DIR, f"input_{temp_id}_{file.filename}")
        temp_compressed_path = os.path.join(TEMP_DIR, f"compressed_{temp_id}_{file.filename}")
        download_filename = file.filename  # Keep original filename
        
        # Save and compress
        file.save(input_path)
        files_to_cleanup.append(input_path)
        
        compressor = HuffmanCompressor()
        compressor.compress_file(input_path, temp_compressed_path)
        files_to_cleanup.append(temp_compressed_path)
        
        # Return the compressed file with original filename
        return send_file(
            temp_compressed_path, 
            as_attachment=True, 
            download_name=download_filename,
            mimetype='application/octet-stream'
        )
        
    except ValueError as e:
        flash(f'Validation Error: {str(e)}', 'error')
    except Exception as e:
        flash(f'Compression Error: {str(e)}', 'error')
        
    return redirect(url_for('index'))

@app.route('/decompress', methods=['POST'])
def decompress():
    """Handle file decompression requests."""
    global files_to_cleanup
    
    if 'file' not in request.files:
        flash('No file uploaded.', 'error')
        return redirect(url_for('index'))
        
    file = request.files['file']
    if file.filename == '':
        flash('No file selected.', 'error')
        return redirect(url_for('index'))
        
    try:
        # Define paths with unique temporary names during processing
        temp_id = str(uuid.uuid4())[:8]
        input_path = os.path.join(TEMP_DIR, f"input_{temp_id}_{file.filename}")
        
        # For decompression, keep the same filename
        output_filename = file.filename
            
        temp_output_path = os.path.join(TEMP_DIR, f"output_{temp_id}_{output_filename}")
        
        # Save and decompress
        file.save(input_path)
        files_to_cleanup.append(input_path)
        
        compressor = HuffmanCompressor()
        compressor.decompress_file(input_path, temp_output_path)
        files_to_cleanup.append(temp_output_path)
        
        # Return the decompressed file
        return send_file(
            temp_output_path, 
            as_attachment=True, 
            download_name=output_filename,
            mimetype='text/plain'
        )
        
    except ValueError as e:
        flash(f'Validation Error: {str(e)}', 'error')
    except Exception as e:
        flash(f'Decompression Error: {str(e)} (Make sure you uploaded a valid compressed file)', 'error')
        
    return redirect(url_for('index'))

@app.route('/info', methods=['GET'])
def info():
    """Return API information."""
    return jsonify({
        'name': 'Huffman File Compressor',
        'version': '1.0',
        'endpoints': {
            '/': 'Web interface',
            '/compress': 'POST - Upload file to compress',
            '/decompress': 'POST - Upload file to decompress'
        }
    })

if __name__ == '__main__':
    print("\n" + "="*60)
    print("🚀 Starting Huffman Compression Web Interface...")
    print("="*60)
    print("📱 Open your browser to: http://localhost:5000")
    print("📊 API Info at: http://localhost:5000/info")
    print("="*60 + "\n")
    app.run(debug=True, host='0.0.0.0', port=5000, use_reloader=False)
