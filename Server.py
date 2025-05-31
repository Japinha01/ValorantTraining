import json
import sqlite3
from http.server import BaseHTTPRequestHandler, HTTPServer
from urllib.parse import parse_qs
from http import cookies
import time
import hashlib
import uuid

DB_NAME = 'ponto.db'

# --- Banco SQLite ---
def init_db():
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    # Usuários
    c.execute('''
    CREATE TABLE IF NOT EXISTS usuarios (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        username TEXT UNIQUE NOT NULL,
        senha_hash TEXT NOT NULL
    )
    ''')
    # Sessões (cookie de sessão)
    c.execute('''
    CREATE TABLE IF NOT EXISTS sessoes (
        session_id TEXT PRIMARY KEY,
        usuario_id INTEGER,
        ultimo_acesso INTEGER,
        FOREIGN KEY(usuario_id) REFERENCES usuarios(id)
    )
    ''')
    # Registros de ponto
    c.execute('''
    CREATE TABLE IF NOT EXISTS registros (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        usuario_id INTEGER,
        tipo TEXT,  -- checkin, pausa, retomar, finalizar
        timestamp INTEGER,
        FOREIGN KEY(usuario_id) REFERENCES usuarios(id)
    )
    ''')
    conn.commit()
    conn.close()

def hash_senha(senha):
    return hashlib.sha256(senha.encode()).hexdigest()

def criar_usuario(username, senha):
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    try:
        c.execute("INSERT INTO usuarios (username, senha_hash) VALUES (?, ?)", (username, hash_senha(senha)))
        conn.commit()
        return True
    except sqlite3.IntegrityError:
        return False
    finally:
        conn.close()

def validar_login(username, senha):
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute("SELECT id, senha_hash FROM usuarios WHERE username = ?", (username,))
    user = c.fetchone()
    conn.close()
    if user and user[1] == hash_senha(senha):
        return user[0]  # retorna id do usuário
    return None

def criar_sessao(usuario_id):
    session_id = str(uuid.uuid4())
    ts = int(time.time())
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute("INSERT INTO sessoes (session_id, usuario_id, ultimo_acesso) VALUES (?, ?, ?)", (session_id, usuario_id, ts))
    conn.commit()
    conn.close()
    return session_id

def obter_usuario_por_sessao(session_id):
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    ts = int(time.time())
    c.execute("SELECT usuario_id FROM sessoes WHERE session_id = ?", (session_id,))
    row = c.fetchone()
    if row:
        # Atualiza ultimo acesso
        c.execute("UPDATE sessoes SET ultimo_acesso = ? WHERE session_id = ?", (ts, session_id))
        conn.commit()
        usuario_id = row[0]
    else:
        usuario_id = None
    conn.close()
    return usuario_id

def registrar_acao(usuario_id, tipo):
    ts = int(time.time())
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute("INSERT INTO registros (usuario_id, tipo, timestamp) VALUES (?, ?, ?)", (usuario_id, tipo, ts))
    conn.commit()
    conn.close()

def relatorio(usuario_id):
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute("SELECT tipo, datetime(timestamp, 'unixepoch', 'localtime') FROM registros WHERE usuario_id = ? ORDER BY timestamp DESC LIMIT 10", (usuario_id,))
    rows = c.fetchall()
    conn.close()
    return rows

# --- Servidor HTTP ---

class Handler(BaseHTTPRequestHandler):
    def _set_headers(self, status=200, content_type='application/json', cookies_out=None):
        self.send_response(status)
        self.send_header('Content-type', content_type)
        if cookies_out:
            for morsel in cookies_out.values():
                self.send_header('Set-Cookie', morsel.OutputString())
        self.end_headers()

    def _parse_cookies(self):
        if "Cookie" in self.headers:
            c = cookies.SimpleCookie(self.headers["Cookie"])
            return c
        return None

    def _get_session_usuario(self):
        c = self._parse_cookies()
        if c and 'session_id' in c:
            session_id = c['session_id'].value
            return obter_usuario_por_sessao(session_id)
        return None

    def _ler_post_json(self):
        length = int(self.headers.get('Content-Length', 0))
        if length > 0:
            data = self.rfile.read(length)
            return json.loads(data)
        return {}

    def do_OPTIONS(self):
        # Permitir CORS para testes com frontend separado
        self.send_response(200)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.end_headers()

    def do_POST(self):
        if self.path == '/login':
            data = self._ler_post_json()
            username = data.get('username')
            senha = data.get('password')
            if not username or not senha:
                self._set_headers(400)
                self.wfile.write(json.dumps({'erro': 'Usuário e senha são obrigatórios'}).encode())
                return

            usuario_id = validar_login(username, senha)
            if usuario_id:
                session_id = criar_sessao(usuario_id)
                cookie = cookies.SimpleCookie()
                cookie['session_id'] = session_id
                cookie['session_id']['path'] = '/'
                # cookie['session_id']['httponly'] = True  # Melhor ativar em produção
                self._set_headers(200, cookies_out=cookie)
                self.wfile.write(json.dumps({'status': 'Login realizado com sucesso'}).encode())
            else:
                self._set_headers(401)
                self.wfile.write(json.dumps({'erro': 'Usuário ou senha inválidos'}).encode())

        else:
            usuario_id = self._get_session_usuario()
            if not usuario_id:
                self._set_headers(401)
                self.wfile.write(json.dumps({'erro': 'Usuário não autenticado'}).encode())
                return

            if self.path == '/checkin':
                registrar_acao(usuario_id, 'checkin')
                self._set_headers()
                self.wfile.write(json.dumps({'status': 'Check-in registrado'}).encode())

            elif self.path == '/pausar':
                registrar_acao(usuario_id, 'pausar')
                self._set_headers()
                self.wfile.write(json.dumps({'status': 'Pausa registrada'}).encode())

            elif self.path == '/retomar':
                registrar_acao(usuario_id, 'retomar')
                self._set_headers()
                self.wfile.write(json.dumps({'status': 'Retomada registrada'}).encode())

            elif self.path == '/finalizar':
                registrar_acao(usuario_id, 'finalizar')
                rel = relatorio(usuario_id)
                texto_relatorio = "\n".join([f"{t[1]} - {t[0]}" for t in rel])
                self._set_headers()
                self.wfile.write(json.dumps({'relatorio': texto_relatorio}).encode())

            elif self.path == '/logout':
                # Expirar cookie e apagar sessão
                c = self._parse_cookies()
                if c and 'session_id' in c:
                    session_id = c['session_id'].value
                    conn = sqlite3.connect(DB_NAME)
                    cur = conn.cursor()
                    cur.execute("DELETE FROM sessoes WHERE session_id = ?", (session_id,))
                    conn.commit()
                    conn.close()

                cookie = cookies.SimpleCookie()
                cookie['session_id'] = ''
                cookie['session_id']['path'] = '/'
                cookie['session_id']['max-age'] = 0
                self._set_headers(200, cookies_out=cookie)
                self.wfile.write(json.dumps({'status': 'Logout realizado'}).encode())

            else:
                self._set_headers(404)
                self.wfile.write(json.dumps({'erro': 'Rota não encontrada'}).encode())

    def do_GET(self):
        # Endpoint simples para testar se está logado e obter nome do usuário
        if self.path == '/me':
            usuario_id = self._get_session_usuario()
            if not usuario_id:
                self._set_headers(401)
                self.wfile.write(json.dumps({'erro': 'Usuário não autenticado'}).encode())
                return
            conn = sqlite3.connect(DB_NAME)
            c = conn.cursor()
            c.execute("SELECT username FROM usuarios WHERE id = ?", (usuario_id,))
            user = c.fetchone()
            conn.close()
            if user:
                self._set_headers(200)
                self.wfile.write(json.dumps({'username': user[0]}).encode())
            else:
                self._set_headers(404)
                self.wfile.write(json.dumps({'erro': 'Usuário não encontrado'}).encode())
        else:
            self._set_headers(404)
            self.wfile.write(json.dumps({'erro': 'Rota não encontrada'}).encode())


if __name__ == '__main__':
    print("Iniciando banco...")
    init_db()
    print("Banco pronto. Iniciando servidor em http://localhost:8080")
    server = HTTPServer(('localhost', 8080), Handler)
    server.serve_forever()
