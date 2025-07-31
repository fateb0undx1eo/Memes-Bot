import threading
from flask import Flask
import os

app = Flask(__name__)

@app.route('/')
def home():
    return "Meme Bot is running! 🚀"

def run_webserver():
    port = int(os.environ.get('PORT', 8080))
    app.run(host='0.0.0.0', port=port)

def keep_alive():
    t = threading.Thread(target=run_webserver)
    t.daemon = True
    t.start()
