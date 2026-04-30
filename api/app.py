import os
from flask import Flask, render_template, request, jsonify
from imagekitio import ImageKit

# Standard Vercel pathing
api_dir = os.path.dirname(os.path.abspath(__file__))
app = Flask(__name__, template_folder=os.path.join(os.path.dirname(api_dir), 'templates'))

# --- IMAGEKIT INITIALIZATION (FIXED PARAMETERS) ---
def get_ik():
    pub = os.environ.get("IK_PUBLIC_KEY")
    pri = os.environ.get("IK_PRIVATE_KEY")
    url = os.environ.get("IK_URL_ENDPOINT")
    
    if not all([pub, pri, url]):
        print("CRITICAL: Missing Environment Variables")
        return None
    
    # The SDK expects these exact argument names:
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
        return jsonify({"error": "IK Setup Failed"}), 500
    try:
        # Fetch files from ImageKit
        files_res = ik.list_files({"path": "/"})
        # Note: Depending on SDK version, files might be in files_res.list or just files_res
        files = getattr(files_res, 'list', files_res)
        
        reports_list = []
        for f in files:
            if hasattr(f, 'tags') and f.tags:
                reports_list.append({
                    "id": f.file_id,
                    "title": f.tags[0],
                    "year": f.tags[1] if len(f.tags) > 1 else "2026",
                    "url": f.url,
                    "type": f.name.split('.')[-1].upper()
                })
        return jsonify(reports_list)
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/upload', methods=['POST'])
def upload():
    if not ik:
        return jsonify({"error": "IK Not Initialized"}), 500
    try:
        file = request.files.get('file')
        title = request.form.get('title')
        year = request.form.get('year')

        if not file:
            return jsonify({"error": "No file"}), 400

        # Upload and Tag
        ik.upload_file(
            file=file.read(),
            file_name=file.filename,
            options={
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