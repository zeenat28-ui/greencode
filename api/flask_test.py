from flask import Flask, request, jsonify
import os

app = Flask(__name__)

@app.route('/api/health')
def health():
    return jsonify({'status': 'healthy', 'version': '2.0.0'})

@app.route('/api/<path:path>', methods=['GET', 'POST', 'OPTIONS'])
def api_handler(path):
    if request.method == 'OPTIONS':
        return '', 200
    return jsonify({'message': 'API endpoint', 'path': path})

# Vercel expects 'app' or 'application'
application = app
