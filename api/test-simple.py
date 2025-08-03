from flask import Flask

app = Flask(__name__)

@app.route('/')
def hello():
    return '<h1>Test Vercel - Système Discord Backup</h1><p>Si vous voyez ce message, la configuration de base fonctionne !</p>'

# Point d'entrée pour Vercel
if __name__ == '__main__':
    app.run(debug=True)