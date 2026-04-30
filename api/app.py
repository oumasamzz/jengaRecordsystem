import os
from flask import Flask, render_template, request, jsonify
from imagekitio import ImageKit

# Standard Vercel pathing
api_dir = os.path.dirname(os.path.abspath(__file__))
app = Flask(__name__, template_folder=os.path.join(os.path.dirname(api_dir), 'templates'))

# --- IMAGEKIT INITIALIZATION (V5+ SYNTAX) ---
def get_ik():
    pub = os.environ.get("IK_PUBLIC_KEY")
    pri = os.environ.get("IK_PRIVATE_KEY")
    url = os.environ.get("IK_URL_ENDPOINT", "https://ik.imagekit.io/je7r0ptq76/jengareports/")
    
    if not pri:
        print("CRITICAL: IK_PRIVATE_KEY is missing from environment.")
        return None
    
    # In newer SDK versions, private_key is the primary required argument.
    # url_endpoint and public_key can often be passed as keyword arguments.
    return ImageKit(
        private_key=pri,
        public_key=pub,
        url_endpoint=url
    )

ik = get_ik()

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/api/reports', methods=['GET'])
def get_reports():
    if not ik:
        return jsonify({"error": "Backend not initialized"}), 500
    try:
        # Use ik.list_files (standard) or ik.files.list (v4+)
        # If one fails, the other is usually the correct one for your version.
        try:
            files_res = ik.list_files({"path": "/"})
        except AttributeError:
            files_res = ik.files.list({"path": "/"})

        # Ensure we handle the response object correctly
        files = getattr(files_res, 'list', files_res) if not isinstance(files_res, list) else files_res
        
        reports_list = []
        for f in files:
            # Safely handle different attribute styles (dict vs object)
            tags = getattr(f, 'tags', []) if not isinstance(f, dict) else f.get('tags', [])
            file_id = getattr(f, 'file_id', None) if not isinstance(f, dict) else f.get('fileId')
            file_url = getattr(f, 'url', '') if not isinstance(f, dict) else f.get('url')
            name = getattr(f, 'name', 'file') if not isinstance(f, dict) else f.get('name')

            if tags:
                reports_list.append({
                    "id": file_id,
                    "title": tags[0],
                    "year": tags[1] if len(tags) > 1 else "2026",
                    "url": file_url,
                    "type": name.split('.')[-1].upper()
                })
        return jsonify(reports_list)
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/upload', methods=['POST'])
def upload():
    if not ik: return jsonify({"error": "Setup fail"}), 500
    try:
        file = request.files.get('file')
        title = request.form.get('title')
        year = request.form.get('year')

        # Use ik.upload_file (standard) or ik.files.upload (v4+)
        upload_method = getattr(ik, 'upload_file', None) or ik.files.upload
        
        upload_method(
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
        delete_method = getattr(ik, 'delete_file', None) or ik.files.delete
        delete_method(file_id)
        return jsonify({"success": True})
    except Exception as e:
        return jsonify({"error": str(e)}), 500