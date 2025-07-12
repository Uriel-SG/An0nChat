from flask import Flask, render_template_string, request, jsonify, send_from_directory, redirect, url_for
from werkzeug.utils import secure_filename
from datetime import datetime
import json
import sqlite3
import os
import html

app = Flask(__name__)
app.config['UPLOAD_FOLDER'] = 'uploads'
app.config['MAX_CONTENT_LENGTH'] = 2 * 1024 * 1024  # 2MB limit
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif', 'pdf', 'txt'}

DB_PATH = 'chat_log.db'
MAX_MESSAGES = 3000

os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

# --- Database setup ---
def init_db():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS messages (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user TEXT NOT NULL,
        text TEXT NOT NULL,
        time TEXT NOT NULL
    )''')
    conn.commit()
    conn.close()

def get_messages(limit=100):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute('SELECT user, text, time FROM messages ORDER BY id DESC LIMIT ?', (limit,))
    rows = c.fetchall()
    conn.close()
    # restituisci in ordine cronologico
    return [dict(user=row[0], text=row[1], time=row[2]) for row in reversed(rows)]

def add_message(user, text, time):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute('INSERT INTO messages (user, text, time) VALUES (?, ?, ?)', (user, text, time))
    conn.commit()
    # Limita il numero di messaggi
    c.execute('SELECT COUNT(*) FROM messages')
    count = c.fetchone()[0]
    if count > MAX_MESSAGES:
        # Elimina i messaggi più vecchi
        c.execute('DELETE FROM messages WHERE id IN (SELECT id FROM messages ORDER BY id ASC LIMIT ?)', (count - MAX_MESSAGES,))
        conn.commit()
    conn.close()

def clear_messages():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute('DELETE FROM messages')
    conn.commit()
    conn.close()

init_db()

html_page = """
<!doctype html>
<html>
<head>
    <title>An0nChat</title>
    <meta name="viewport" content="width=device-width, initial-scale=1, maximum-scale=1">
    <link rel="manifest" href="{{ url_for('static', filename='manifest.json') }}">
    <script>
        if ('serviceWorker' in navigator) {
            window.addEventListener('load', () => {
                navigator.serviceWorker.register('/static/service-worker.js');
            });
        }
    </script>
    <style>
        :root {
            --bg: #f0f0f0;
            --fg: #000;
            --container-bg: #ffffff;
            --chat-bg: #fdfdfd;
            --msg-odd: #f8f8f8;
            --msg-even: #e6f2ff;
            --input-bg: #fff;
            --input-fg: #000;
            --button-bg: #ddd;
            --button-hover: #ccc;
            --link-color: #007bff;
        }
        body.dark {
            --bg: #121212;
            --fg: #f0f0f0;
            --container-bg: #1e1e1e;
            --chat-bg: #2a2a2a;
            --msg-odd: #2d2d2d;
            --msg-even: #242424;
            --input-bg: #333;
            --input-fg: #fff;
            --button-bg: #444;
            --button-hover: #666;
            --link-color: #80d4ff;
        }
        body {
            font-family: sans-serif;
            padding: 20px;
            background: var(--bg);
            color: var(--fg);
            display: flex;
            justify-content: center;
        }
        .container {
            max-width: 600px;
            width: 100%;
            background: var(--container-bg);
            padding: 20px;
            border-radius: 10px;
            box-shadow: 0 0 10px rgba(0,0,0,0.2);
        }
        #chatbox {
            border: 1px solid #ccc;
            height: 300px;
            overflow-y: scroll;
            padding: 10px;
            background: var(--chat-bg);
            margin-bottom: 10px;
        }
        .msg:nth-child(odd) {
            background-color: var(--msg-odd);
            padding: 5px;
        }
        .msg:nth-child(even) {
            background-color: var(--msg-even);
            padding: 5px;
        }
        header {
            display: flex;
            align-items: center;
            margin-bottom: 20px;
        }
        header img {
            height: 50px;
            margin-right: 15px;
            border-radius: 50%;
        }
        header h2 {
            margin: 0;
            color: var(--fg);
        }
        #controls {
            display: flex;
            justify-content: space-between;
            margin-top: 10px;
        }
        input[type="text"], input[type="file"] {
            background: var(--input-bg);
            color: var(--input-fg);
            border: 1px solid #999;
            padding: 8px;
            margin: 5px 0;
            border-radius: 5px;
        }
        button {
            background: var(--button-bg);
            color: var(--input-fg);
            border: none;
            padding: 10px 15px;
            border-radius: 5px;
            cursor: pointer;
            transition: background 0.3s;
        }
        button:hover {
            background: var(--button-hover);
        }
        a {
            color: var(--link-color);
            text-decoration: none;
        }
        a:hover {
            text-decoration: underline;
        }
        #inputRow {
            display: flex;
            gap: 10px;
            margin-bottom: 10px;
        }
        #message {
            flex: 1;
        }
        @media (max-width: 480px) {
            body {
                padding: 10px;
            }
            .container {
                padding: 15px;
            }
            #username {
                width: 100% !important;
                margin-bottom: 10px;
            }
            #inputRow {
                flex-direction: column;
            }
            #message, #inputRow button {
                width: 100%;
                box-sizing: border-box;
                margin-bottom: 10px;
            }
            #controls {
                flex-direction: column;
                gap: 10px;
            }
            #controls input[type="file"], #controls button {
                width: 100%;
            }
        }
    </style>
</head>
<body>
    <div class="container">
        <header>
            <img src="{{ url_for('static', filename='anon.jpg') }}" alt="Logo">
            <h2>An0nChat</h2>
        </header>

        <div style="text-align: right; margin-bottom: 10px;">
            <button onclick="toggleTheme()" id="themeBtn">🌙 Dark Theme</button>
        </div>

        <div id="chatbox"></div>

        <input type="text" id="username" placeholder="Name (optional)" style="width: 25%; margin-bottom: 10px;">

        <div id="inputRow">
            <input type="text" id="message" placeholder="Write a message..." onkeydown="handleKey(event)">
            <button type="button" onclick="sendMessage()">Send</button>
        </div>

        <div id="controls">
            <input type="file" id="fileInput">
            <button onclick="clearChat()">🧹 Clear chat for everyone</button>
        </div>
    </div>

    <noscript>
        <div class="container">
            <p>This chat requires JavaScript to function fully.</p>
        </div>
    </noscript>

    <script>
        const usernameInput = document.getElementById('username');
        usernameInput.value = localStorage.getItem('username') || '';
        usernameInput.addEventListener('input', () => {
            localStorage.setItem('username', usernameInput.value);
        });

        let lastMsgCount = 0;

        function updateChat() {
            fetch('/messages')
                .then(response => response.json())
                .then(data => {
                    const chatbox = document.getElementById('chatbox');
                    if (data.messages.length > lastMsgCount) {
                        lastMsgCount = data.messages.length;
                    }
                    chatbox.innerHTML = data.messages.map(m => {
                        let content = m.text;
                        if (m.text.startsWith("/file/")) {
                            const filename = m.text.replace("/file/", "");
                            content = `<a href="/file/${filename}" target="_blank">📎 ${filename}</a>`;
                        }
                        return `<div class="msg"><b>${m.time} ${m.user}:</b> ${content}</div>`;
                    }).join('');
                    chatbox.scrollTop = chatbox.scrollHeight;
                });
        }

        function sendMessage() {
            const user = usernameInput.value || "Anonymous";
            const text = document.getElementById('message').value.trim();
            const fileInput = document.getElementById('fileInput');

            if (fileInput.files.length > 0) {
                const formData = new FormData();
                formData.append("file", fileInput.files[0]);
                formData.append("user", user);

                fetch("/upload", {
                    method: "POST",
                    body: formData
                }).then(() => {
                    fileInput.value = "";
                    document.getElementById('message').value = "";
                    updateChat();
                });

            } else if (text) {
                fetch('/send', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ user: user, text: text })
                }).then(() => {
                    document.getElementById('message').value = '';
                    updateChat();
                });
            }
        }

        function handleKey(event) {
            if (event.key === "Enter") {
                event.preventDefault();
                sendMessage();
            }
        }

        function clearChat() {
            fetch('/clear', { method: 'POST' }).then(() => {
                lastMsgCount = 0;
                updateChat();
            });
        }

        function toggleTheme() {
            const isDark = document.body.classList.toggle("dark");
            localStorage.setItem("theme", isDark ? "dark" : "light");
            document.getElementById("themeBtn").innerText = isDark ? "☀️ Bright Theme" : "🌙 Dark Theme";
        }

        window.addEventListener("DOMContentLoaded", () => {
            const savedTheme = localStorage.getItem("theme");
            if (savedTheme === "dark") {
                document.body.classList.add("dark");
                document.getElementById("themeBtn").innerText = "☀️ Bright Theme";
            }
            updateChat();
            setInterval(updateChat, 1000);
        });
    </script>
</body>
</html>
"""

@app.route('/')
def index():
    return render_template_string(html_page)

@app.route('/noscript', methods=['GET', 'POST'])
def noscript():
    if request.method == 'POST':
        user = html.escape(request.form.get('user', 'Anon'))
        text = html.escape(request.form.get('text', ''))
        time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        if text:
            add_message(user, text, time)
        return redirect(url_for('noscript'))

    form = """
    <form method="POST">
      <input name="user" placeholder="Nome">
      <input name="text" placeholder="Messaggio">
      <button type="submit">Invia</button>
    </form>
    """
    chat_html = "".join(f"<div><b>{html.escape(m['time'])} {html.escape(m['user'])}:</b> {html.escape(m['text'])}</div>" for m in get_messages(50))
    return f"<html><body>{chat_html}{form}</body></html>"

@app.route('/send', methods=['POST'])
def send():
    data = request.get_json()
    user = html.escape(data.get('user', 'Anon'))
    text = html.escape(data.get('text', ''))
    time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    add_message(user, text, time)
    return '', 204

@app.route('/messages')
def get_messages_route():
    return jsonify(messages=get_messages(100))

@app.route('/clear', methods=['POST'])
def clear():
    clear_messages()
    for f in os.listdir(app.config['UPLOAD_FOLDER']):
        os.remove(os.path.join(app.config['UPLOAD_FOLDER'], f))
    return '', 204

@app.route('/upload', methods=['POST'])
def upload_file():
    if 'file' not in request.files:
        return 'No file part', 400
    file = request.files['file']
    user = html.escape(request.form.get('user', 'Anon'))
    if file.filename == '':
        return 'No file selected', 400
    if allowed_file(file.filename):
        filename = secure_filename(file.filename)
        filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        file.save(filepath)
        time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        add_message(user, f"/file/{filename}", time)
        return '', 204
    return 'File type not allowed', 400

@app.route('/file/<filename>')
def uploaded_file(filename):
    return send_from_directory(app.config['UPLOAD_FOLDER'], filename)

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS



if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8080, debug=False)
