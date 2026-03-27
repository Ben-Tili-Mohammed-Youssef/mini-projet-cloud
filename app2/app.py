from flask import Flask, request, jsonify

app = Flask(__name__)

# Stockage temporaire en mémoire (juste pour tester)
tasks = []
next_id = 1

@app.route('/tasks', methods=['GET'])
def get_tasks():
    return jsonify(tasks)

@app.route('/tasks', methods=['POST'])
def create_task():
    global next_id
    data = request.get_json()
    if not data or 'title' not in data:
        return jsonify({'error': 'title is required'}), 400
    task = {
        'id': next_id,
        'title': data['title'],
        'completed': data.get('completed', False)
    }
    tasks.append(task)
    next_id += 1
    return jsonify(task), 201

@app.route('/tasks/<int:task_id>', methods=['DELETE'])
def delete_task(task_id):
    global tasks
    task = next((t for t in tasks if t['id'] == task_id), None)
    if task is None:
        return jsonify({'error': 'task not found'}), 404
    tasks = [t for t in tasks if t['id'] != task_id]
    return jsonify({'result': 'task deleted'}), 200

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
