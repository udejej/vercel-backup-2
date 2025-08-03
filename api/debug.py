from flask import Flask, render_template, jsonify
import os
from datetime import datetime

app = Flask(__name__)

@app.route('/debug')
def debug():
    """Route de debug pour tester les déploiements Vercel"""
    return jsonify({
        'status': 'OK',
        'timestamp': datetime.now().isoformat(),
        'template_path': os.path.exists('templates/index.html'),
        'files': os.listdir('.') if os.path.exists('.') else [],
        'message': 'Si vous voyez ce message, Vercel fonctionne correctement'
    })

@app.route('/test-template')
def test_template():
    """Test du template"""
    return render_template('index.html')

if __name__ == '__main__':
    app.run(debug=True)