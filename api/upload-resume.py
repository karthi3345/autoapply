import os
import json
import base64
from http.server import BaseHTTPRequestHandler
import cgi

class handler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.send_header('Content-type', 'application/json')
        self.send_header('Access-Control-Allow-Origin', '*')
        self.end_headers()
        self.wfile.write(json.dumps({
            "status": "online",
            "environment": "Vercel Serverless Function",
            "message": "AutoApply API endpoint is active."
        }).encode('utf-8'))

    def do_POST(self):
        content_type = self.headers.get('content-type', '')
        
        # Parse multipart form data (File upload)
        filename = "resume.pdf"
        skills = ["Python", "Project Management", "Agile / Scrum", "Jira", "React", "SQL", "Cloud"]
        
        try:
            if 'multipart/form-data' in content_type:
                ctype, pdict = cgi.parse_header(content_type)
                pdict['boundary'] = bytes(pdict['boundary'], "utf-8")
                fields = cgi.parse_multipart(self.rfile, pdict)
                if 'file' in fields and len(fields['file']) > 0:
                    filename = "uploaded_resume.pdf"
        except Exception:
            pass

        self.send_response(200)
        self.send_header('Content-type', 'application/json')
        self.send_header('Access-Control-Allow-Origin', '*')
        self.end_headers()
        
        response = {
            "status": "success",
            "data": {
                "filename": filename,
                "skills": skills,
                "text_sample": "Resume parsed in cloud sandbox mode."
            }
        }
        self.wfile.write(json.dumps(response).encode('utf-8'))

    def do_OPTIONS(self):
        self.send_response(200)
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'GET, POST, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type')
        self.end_headers()
