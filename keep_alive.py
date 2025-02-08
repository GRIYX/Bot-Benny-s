from flask import Flask
from threading import Thread

app = Flask('')

@app.route('/')
def home():
     return "Le bot est en ligne !"

def run():
     app.run(host='0.0.0.0', port=8080)

def keep_alive():
    t = Thread(target=run)  # <-- Vérifie que cette ligne n'a pas d'espace en trop devant
    t.start()  # <-- Assure-toi que cette ligne est bien indentée à ce niveau
