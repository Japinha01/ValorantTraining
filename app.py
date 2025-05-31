from flask import Flask, request, jsonify, render_template, session, redirect, url_for
from datetime import datetime, timedelta
import requests
import os
from functools import wraps

app = Flask(__name__)
app.secret_key = 'sua_chave_super_secreta_aqui'

USUARIOS = {
    'Japa': 'japa19',
    'White': 'white12',
    'Tata': 'tata15',
    'Debora': 'deb23',
    'Iza': 'iza72',
}

sessoes = {}

TELEGRAM_TOKEN = os.getenv('TELEGRAM_TOKEN', '8015668113:AAHW99YDOsrecBE9Ezh7pz3TvlhTHfEMcaE')
CHAT_ID = os.getenv('TELEGRAM_CHAT_ID', '1742433608')

def notificar_mensagem(mensagem):
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    payload = {'chat_id': CHAT_ID, 'text': mensagem}
    try:
        requests.post(url, data=payload)
    except Exception as e:
        print(f"Erro ao enviar mensagem para Telegram: {e}")

def calcular_tempo_total(registro):
    inicio = datetime.strptime(registro['inicio'], '%Y-%m-%d %H:%M:%S')
    fim = datetime.strptime(registro['fim'], '%Y-%m-%d %H:%M:%S')
    total = fim - inicio
    for pausa in registro['pausas']:
        if pausa['retomada']:
            inicio_pausa = datetime.strptime(pausa['inicio'], '%Y-%m-%d %H:%M:%S')
            fim_pausa = datetime.strptime(pausa['retomada'], '%Y-%m-%d %H:%M:%S')
            total -= (fim_pausa - inicio_pausa)
    return total

def calcular_tempo_pausas(registro):
    pausa_total = timedelta(0)
    for pausa in registro['pausas']:
        if pausa['retomada']:
            inicio_pausa = datetime.strptime(pausa['inicio'], '%Y-%m-%d %H:%M:%S')
            fim_pausa = datetime.strptime(pausa['retomada'], '%Y-%m-%d %H:%M:%S')
            pausa_total += fim_pausa - inicio_pausa
        else:
            inicio_pausa = datetime.strptime(pausa['inicio'], '%Y-%m-%d %H:%M:%S')
            pausa_total += datetime.now() - inicio_pausa
    return pausa_total

def formatar_timedelta(td):
    total_segundos = int(td.total_seconds())
    horas = total_segundos // 3600
    minutos = (total_segundos % 3600) // 60
    segundos = total_segundos % 60
    return f"{horas}h {minutos}m {segundos}s"

def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'username' not in session:
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function

@app.route('/')
def home():
    if 'username' in session:
        return redirect(url_for('ponto'))
    return redirect(url_for('login'))

@app.route('/ponto')
@login_required
def ponto():
    return render_template('index.html', nome=session['username'])

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        if username in USUARIOS and USUARIOS[username] == password:
            session['username'] = username
            return redirect(url_for('ponto'))
        else:
            return render_template('login.html', erro='Usuário ou senha inválidos')
    return render_template('login.html')

@app.route('/logout')
def logout():
    session.pop('username', None)
    return redirect(url_for('login'))

@app.route('/checkin', methods=['POST'])
@login_required
def checkin():
    nome = session['username']
    sessoes[nome] = {
        'inicio': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
        'pausas': [],
        'fim': None
    }
    notificar_mensagem(f'✅ {nome} fez CHECK-IN às {sessoes[nome]["inicio"]}')
    return jsonify({'status': 'Check-in registrado'})

@app.route('/pausar', methods=['POST'])
@login_required
def pausar():
    nome = session['username']
    if nome in sessoes:
        sessoes[nome]['pausas'].append({
            'inicio': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            'retomada': None
        })
        notificar_mensagem(f'⏸ {nome} PAUSOU às {sessoes[nome]["pausas"][-1]["inicio"]}')
        return jsonify({'status': 'Pausa registrada'})
    return jsonify({'erro': 'Usuário não encontrado'}), 404

@app.route('/retomar', methods=['POST'])
@login_required
def retomar():
    nome = session['username']
    if nome in sessoes and sessoes[nome]['pausas']:
        sessoes[nome]['pausas'][-1]['retomada'] = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        notificar_mensagem(f'▶️ {nome} RETOMOU às {sessoes[nome]["pausas"][-1]["retomada"]}')
        return jsonify({'status': 'Retomada registrada'})
    return jsonify({'erro': 'Usuário ou pausa não encontrados'}), 404

@app.route('/finalizar', methods=['POST'])
@login_required
def finalizar():
    nome = session['username']
    if nome in sessoes:
        sessoes[nome]['fim'] = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        registro = sessoes[nome]
        tempo_ativo = calcular_tempo_total(registro)
        tempo_pausa = calcular_tempo_pausas(registro)
        qtd_pausas = len(registro['pausas'])
        data_inicio = registro['inicio'].split(' ')[0]
        mensagem_relatorio = (
            f"🏁 {nome} FINALIZOU às {registro['fim']}\n"
            f"📅 Data: {data_inicio}\n"
            f"⏰ Início: {registro['inicio']}\n"
            f"⏰ Fim: {registro['fim']}\n"
            f"⏱ Tempo total ativo: {tempo_ativo}\n"
            f"⏸ Tempo total de pausas: {tempo_pausa}\n"
            f"🔁 Quantidade de pausas: {qtd_pausas}"
        )
        notificar_mensagem(mensagem_relatorio)
        return jsonify({'status': 'Finalizado', 'relatorio': mensagem_relatorio})
    return jsonify({'erro': 'Usuário não encontrado'}), 404

@app.route('/relatorio', methods=['GET'])
@login_required
def relatorio():
    nome = session['username']
    if nome in sessoes:
        return jsonify({nome: sessoes[nome]})
    return jsonify({'erro': 'Usuário não encontrado'}), 404
