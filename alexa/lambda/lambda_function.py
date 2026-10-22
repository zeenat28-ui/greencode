"""
ASK Toolkit Lambda Handler - Redirects to FastAPI Backend

This handler is used by ASK Toolkit for local debugging.
In production, requests go directly to /api/alexa/skill
"""

import json
import urllib.request
import os

BACKEND_URL = os.environ.get('BACKEND_URL', 'http://localhost:8000')

def lambda_handler(event, context):
    """Forward Alexa request to FastAPI backend"""
    try:
        req = urllib.request.Request(
            f'{BACKEND_URL}/api/alexa/skill',
            data=json.dumps(event).encode('utf-8'),
            headers={'Content-Type': 'application/json'}
        )
        response = urllib.request.urlopen(req, timeout=10)
        return json.loads(response.read())
    except Exception as e:
        return {
            'version': '1.0',
            'response': {
                'outputSpeech': {
                    'type': 'PlainText',
                    'text': f'Backend error: {str(e)}'
                },
                'shouldEndSession': True
            }
        }
