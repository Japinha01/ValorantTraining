from flask import Flask, request, jsonify, render_template, session, redirect, url_for
from datetime import datetime, timedelta
import sqlite3
import os
from werkzeug.security import generate_password_hash, check_password_hash
from functools import wraps
import requests

app = Flask(__name__)
app.secret_key = 'TreinoMaster'

DB_NAME = 'ponto.db'
TELEGRAM_TOKEN = os.getenv('TELEGRAM_TOKEN', '8015668113:AAHW99YDOsrecBE9Ezh7pz3TvlhTHfEMcaE')
CHAT_ID = os.getenv('TELEGRAM_CHAT_ID', '1742433608')

# --- Banco de Dados ---
def init_db():
    with sqlite3.connect(DB_NAME) as conn:
        c = conn.cursor()
        c.execute('''CREATE TABLE IF NOT EXISTS usuarios (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        username TEXT UNIQUE NOT NULL,
                        senha_hash TEXT NOT NULL)''')
        c.execute('''CREATE TABLE IF NOT EXISTS registros (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        usuario_id INTEGER,
                        tipo TEXT,
                        timestamp TEXT,
                        FOREIGN KEY(usuario_id) REFERENCES usuarios(id))''')
        conn.commit()

init_db()

# --- Envio para Telegram ---
def notificar_mensagem(mensagem):
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    payload = {'chat_id': CHAT_ID, 'text': mensagem}
    try:
        requests.post(url, data=payload)
    except Exception as e:
        print(f"Erro ao enviar mensagem para Telegram: {e}")

# --- Decorador de Login ---
def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'usuario_id' not in session:
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function

# --- Rotas ---
@app.route('/')
@login_required
def index():
    return render_template('index.html', nome=session['username'])

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        with sqlite3.connect(DB_NAME) as conn:
            c = conn.cursor()
            c.execute('SELECT id, senha_hash FROM usuarios WHERE username = ?', (username,))
            user = c.fetchone()
            if user and password == user[1]:  # ou use check_password_hash(user[1], password)
                session['usuario_id'] = user[0]
                session['username'] = username
                return redirect(url_for('index'))
        return 'Login falhou'
    return render_template('login.html')

@app.route('/logout')
@login_required
def logout():
    session.clear()
    return redirect(url_for('login'))

@app.route('/checkin', methods=['POST'])
@login_required
def checkin():
    usuario_id = session['usuario_id']
    username = session['username']
    timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    tipo = "checkin"
    with sqlite3.connect(DB_NAME) as conn:
        c = conn.cursor()
        c.execute('INSERT INTO registros (usuario_id, tipo, timestamp) VALUES (?, ?, ?)',
                  (usuario_id, tipo, timestamp))
        conn.commit()
    notificar_mensagem(f"✅ {username} fez CHECK-IN às {timestamp}")
    return jsonify({'status': 'ok'})

@app.route('/pausar', methods=['POST'])
@login_required
def pausar():
    usuario_id = session['usuario_id']
    username = session['username']
    timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    tipo = "pausa"
    with sqlite3.connect(DB_NAME) as conn:
        c = conn.cursor()
        c.execute('INSERT INTO registros (usuario_id, tipo, timestamp) VALUES (?, ?, ?)',
                  (usuario_id, tipo, timestamp))
        conn.commit()
    notificar_mensagem(f"⏸ {username} PAUSOU às {timestamp}")
    return jsonify({'status': 'ok'})

@app.route('/retomar', methods=['POST'])
@login_required
def retomar():
    usuario_id = session['usuario_id']
    username = session['username']
    timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    tipo = "retomar"
    with sqlite3.connect(DB_NAME) as conn:
        c = conn.cursor()
        c.execute('INSERT INTO registros (usuario_id, tipo, timestamp) VALUES (?, ?, ?)',
                  (usuario_id, tipo, timestamp))
        conn.commit()
    notificar_mensagem(f"▶ {username} RETOMOU às {timestamp}")
    return jsonify({'status': 'ok'})

@app.route('/finalizar', methods=['POST'])
@login_required
def finalizar():
    usuario_id = session['usuario_id']
    username = session['username']
    timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    tipo = "finalizar"

    with sqlite3.connect(DB_NAME) as conn:
        c = conn.cursor()
        # Pega o último checkin para esta jornada
        c.execute('SELECT timestamp FROM registros WHERE usuario_id = ? AND tipo = "checkin" ORDER BY timestamp DESC LIMIT 1', (usuario_id,))
        row = c.fetchone()
        if not row:
            return jsonify({'status': 'erro', 'mensagem': 'Nenhum check-in encontrado'})

        inicio_checkin = row[0]

        # Salva o finalizar
        c.execute('INSERT INTO registros (usuario_id, tipo, timestamp) VALUES (?, ?, ?)',
                  (usuario_id, tipo, timestamp))

        # Pega todos os eventos após o último checkin
        c.execute('''
            SELECT tipo, timestamp FROM registros 
            WHERE usuario_id = ? AND timestamp >= ? 
            ORDER BY timestamp
        ''', (usuario_id, inicio_checkin))
        eventos = c.fetchall()

    inicio = datetime.strptime(inicio_checkin, '%Y-%m-%d %H:%M:%S')
    fim = datetime.strptime(timestamp, '%Y-%m-%d %H:%M:%S')

    pausas = []
    retomadas = []

    for tipo_evento, ts in eventos:
        dt = datetime.strptime(ts, '%Y-%m-%d %H:%M:%S')
        if tipo_evento == 'pausa':
            pausas.append(dt)
        elif tipo_evento == 'retomar':
            retomadas.append(dt)

    pausa_total = timedelta()
    for p, r in zip(pausas, retomadas):
        if r > p:
            pausa_total += (r - p)

    tempo_total = fim - inicio
    tempo_ativo = tempo_total - pausa_total
    if tempo_ativo.total_seconds() < 0:
        tempo_ativo = timedelta(0)

    relatorio = (
        f"📅 Data: {inicio.date()}\n"
        f"⏰ Início: {inicio.strftime('%Y-%m-%d %H:%M:%S')}\n"
        f"⏰ Fim: {fim.strftime('%Y-%m-%d %H:%M:%S')}\n"
        f"⏱ Tempo total ativo: {str(tempo_ativo)}\n"
        f"⏸ Tempo total de pausas: {str(pausa_total)}\n"
        f"🔁 Quantidade de pausas: {len(pausas)}"
    )

    notificar_mensagem(f"🌟 {username} FINALIZOU às {timestamp}\n\nRELATÓRIO FINAL\n{relatorio}")

    return jsonify({'status': 'ok', 'relatorio': relatorio})

@app.route('/registros')
@login_required
def registros():
    usuario_id = session['usuario_id']
    with sqlite3.connect(DB_NAME) as conn:
        c = conn.cursor()
        c.execute('SELECT tipo, timestamp FROM registros WHERE usuario_id = ? ORDER BY timestamp DESC',
                  (usuario_id,))
        dados = c.fetchall()
    return jsonify(dados)

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)
