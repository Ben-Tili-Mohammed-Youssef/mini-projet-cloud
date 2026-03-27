from flask import Flask, request, jsonify, session
from flask_mysqldb import MySQL
import redis
import time
import json
import uuid

app = Flask(__name__)
app.config['JSON_AS_ASCII'] = False
app.secret_key = 'cle-secrete-123'  # nécessaire pour les sessions

# Config MySQL
app.config['MYSQL_HOST'] = 'db'
app.config['MYSQL_USER'] = 'admin'
app.config['MYSQL_PASSWORD'] = 'admin'
app.config['MYSQL_DB'] = 'tasks'

mysql = MySQL(app)

# Config Redis
cache = redis.Redis(host='redis', port=6379, decode_responses=True)

def init_db():
    retries = 10
    while retries > 0:
        try:
            cur = mysql.connection.cursor()
            cur.execute("""
                CREATE TABLE IF NOT EXISTS tasks (
                    id INT AUTO_INCREMENT PRIMARY KEY,
                    title VARCHAR(255) NOT NULL,
                    done BOOLEAN DEFAULT FALSE
                )
            """)
            mysql.connection.commit()
            cur.close()
            print("Base de données prête !")
            break
        except Exception as e:
            print("MySQL pas encore prêt... on attend ({} essais restants)".format(retries))
            retries -= 1
            time.sleep(5)

with app.app_context():
    init_db()

# -----------------------------------------------
# SESSION STORAGE avec Redis
# -----------------------------------------------

@app.route('/login', methods=['POST'])
def login():
    data = request.get_json()
    username = data.get('username', 'anonyme')

    # Créer un ID de session unique
    session_id = str(uuid.uuid4())

    # Stocker la session dans Redis pour 1 heure
    cache.setex('session:{}'.format(session_id), 3600, username)

    return jsonify({
        "message": "Connecté en tant que {}".format(username),
        "session_id": session_id
    })

@app.route('/me', methods=['GET'])
def me():
    session_id = request.headers.get('Session-Id')
    if not session_id:
        return jsonify({"error": "Pas de session fournie"}), 401

    username = cache.get('session:{}'.format(session_id))
    if not username:
        return jsonify({"error": "Session expirée ou invalide"}), 401

    return jsonify({
        "message": "Bonjour {}".format(username),
        "session_id": session_id
    })

@app.route('/logout', methods=['POST'])
def logout():
    session_id = request.headers.get('Session-Id')
    if session_id:
        cache.delete('session:{}'.format(session_id))
    return jsonify({"message": "Déconnecté !"})

# -----------------------------------------------
# COMPTEUR DE VISITES avec Redis
# -----------------------------------------------

@app.route('/')
def home():
    visits = cache.incr('visits')
    return jsonify({
        "message": "TODO API avec MySQL + Redis !",
        "visites": visits
    })

# -----------------------------------------------
# TASKS avec cache Redis
# -----------------------------------------------

@app.route('/tasks', methods=['GET'])
def get_tasks():
    cached = cache.get('tasks')
    if cached:
        print("Données depuis le cache Redis !")
        return app.response_class(
            response=cached,
            mimetype='application/json'
        )
    cur = mysql.connection.cursor()
    cur.execute("SELECT id, title, done FROM tasks")
    rows = cur.fetchall()
    cur.close()
    tasks = [{"id": r[0], "title": r[1], "done": bool(r[2])} for r in rows]
    cache.setex('tasks', 30, json.dumps(tasks, ensure_ascii=False))
    print("Données depuis MySQL, mises en cache !")
    return jsonify(tasks)

@app.route('/tasks', methods=['POST'])
def add_task():
    data = request.get_json()
    title = data.get("title", "Sans titre")
    cur = mysql.connection.cursor()
    cur.execute("INSERT INTO tasks (title) VALUES (%s)", (title,))
    mysql.connection.commit()
    new_id = cur.lastrowid
    cur.close()
    cache.delete('tasks')
    return jsonify({"id": new_id, "title": title, "done": False}), 201

@app.route('/tasks/<int:task_id>', methods=['DELETE'])
def delete_task(task_id):
    cur = mysql.connection.cursor()
    cur.execute("DELETE FROM tasks WHERE id = %s", (task_id,))
    mysql.connection.commit()
    cur.close()
    cache.delete('tasks')
    return jsonify({"message": "Tâche {} supprimée".format(task_id)})

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)
