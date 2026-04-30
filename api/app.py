import os
from flask import Flask, render_template, request, jsonify
from imagekitio import ImageKit

# Standard Vercel pathing for templates
api_dir = os.path.dirname(os.path.abspath(__file__))
app = Flask(__name__, template_folder=os.path.join(os.path.dirname(api_dir), 'templates'))

# --- IMAGEKIT INITIALIZATION ---
def get_ik():
    pub = os.environ.get("IK_PUBLIC_KEY")
    pri = os.environ.get("IK_PRIVATE_KEY")
    url = os.environ.get("IK_URL_ENDPOINT")
    
    if not all([pub, pri, url]):
        return None
        
    return ImageKit(
        public_key=pub,
        private_key=pri,
        url_endpoint=url
    )

ik = get_ik()

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/api/reports', methods=['GET'])
def get_reports():
    if not ik:
        return jsonify({"error": "ImageKit variables missing in Vercel"}), 500
    try:
        # Fetching files from the 'reports' folder in ImageKit
        files = ik.list_files({"path": "/reports"})
        
        reports_list = []
        for f in files:
            # We use f.tags to store [Title, Year]
            title = f.tags[0] if (f.tags and len(f.tags) > 0) else "Untitled"
            year = f.tags[1] if (f.tags and len(f.tags) > 1) else "N/A"
            
            reports_list.append({
                "id": f.file_id,
                "title": title,
                "year": year,
                "url": f.url,
                "type": f.name.split('.')[-1]
            })
        return jsonify(reports_list)
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/upload', methods=['POST'])
def upload():
    if not ik:
        return jsonify({"error": "ImageKit not configured"}), 500
    try:
        file = request.files.get('file')
        title = request.form.get('title')
        year = request.form.get('year')

        if not file:
            return jsonify({"error": "No file selected"}), 400

        # Uploading to ImageKit and tagging it with Title/Year
        upload_res = ik.upload_file(
            file=file.read(),
            file_name=file.filename,
            options={
                "folder": "/reports",
                "tags": [title, year],
                "use_unique_file_name": True
            }
        )
        return jsonify({"success": True})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/delete/<file_id>', methods=['DELETE'])
def delete(file_id):
    if request.headers.get("X-Admin-Key") != "Tandy254./":
        return jsonify({"error": "Unauthorized"}), 403
    try:
        ik.delete_file(file_id)
        return jsonify({"success": True})
    except Exception as e:
        return jsonify({"error": str(e)}), 500