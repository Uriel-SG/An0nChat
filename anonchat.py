from flask import Flask, render_template_string, request, jsonify, url_for, send_from_directory
from datetime import datetime
import json
import os
from werkzeug.utils import secure_filename

app = Flask(__name__)
CHAT_LOG = "chat_log.json"
UPLOAD_FOLDER = "uploads"
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif', 'pdf', 'txt'}

# Carica messaggi da file all'avvio
if os.path.exists(CHAT_LOG):
    with open(CHAT_LOG, "r", encoding="utf-8") as f:
        messages = json.load(f)
else:
    messages = []

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
                        document.getElementById("notifSound")?.play();
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

@app.route('/send', methods=['POST'])
def send():
    data = request.get_json()
    time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    messages.append({"user": data['user'], "text": data['text'], "time": time})
    save_messages()
    return '', 204

@app.route('/messages')
def get_messages():
    return jsonify(messages=messages)

@app.route('/clear', methods=['POST'])
def clear():
    messages.clear()
    if os.path.exists(CHAT_LOG):
        os.remove(CHAT_LOG)
    for f in os.listdir(UPLOAD_FOLDER):
        os.remove(os.path.join(UPLOAD_FOLDER, f))
    return '', 204

@app.route('/upload', methods=['POST'])
def upload_file():
    if 'file' not in request.files:
        return 'No file part in the request', 400

    file = request.files['file']
    user = request.form.get('user', 'Anonymous')

    if file.filename == '':
        return 'No selected file', 400

    if file and allowed_file(file.filename):
        filename = secure_filename(file.filename)
        filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        file.save(filepath)
        time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        messages.append({"user": user, "text": f"/file/{filename}", "time": time})
        save_messages()
        return '', 204
    else:
        return 'File type not allowed', 400

@app.route('/file/<filename>')
def uploaded_file(filename):
    return send_from_directory(app.config['UPLOAD_FOLDER'], filename)

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def save_messages():
    with open(CHAT_LOG, "w", encoding="utf-8") as f:
        json.dump(messages, f, indent=2, ensure_ascii=False)

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8080, debug=True)
