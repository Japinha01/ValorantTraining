const cronometroEl = document.getElementById('cronometro');
const mensagemEl = document.getElementById('mensagem');
const nome = document.getElementById('nome')?.value || ''; // pega o nome do usuário

let cronometroInterval = null;
let tempoTotal = 0;
let pausado = false;

function formatarTempo(segundos) {
  const h = String(Math.floor(segundos / 3600)).padStart(2, '0');
  const m = String(Math.floor((segundos % 3600) / 60)).padStart(2, '0');
  const s = String(segundos % 60).padStart(2, '0');
  return `${h}:${m}:${s}`;
}

function atualizarCronometroUI() {
  cronometroEl.textContent = formatarTempo(tempoTotal);
}

function iniciarCronometro() {
  if (cronometroInterval) clearInterval(cronometroInterval);
  cronometroInterval = setInterval(() => {
    if (!pausado) {
      tempoTotal++;
      atualizarCronometroUI();
    }
  }, 1000);
}

function pararCronometro() {
  if (cronometroInterval) clearInterval(cronometroInterval);
}

function mostrarMensagem(msg, tipo = 'sucesso') {
  mensagemEl.textContent = msg;
  mensagemEl.className = `mensagem ${tipo}`;
  setTimeout(() => {
    mensagemEl.textContent = '';
    mensagemEl.className = 'mensagem';
  }, 4000);
}

async function enviarAcao(acao) {
  if (!nome) {
    mostrarMensagem('Por favor, informe seu nome', 'erro');
    return;
  }
  try {
    const res = await fetch(`/${acao}`, {
      method: 'POST',
      headers: {'Content-Type': 'application/json'},
      body: JSON.stringify({ nome, tempo: tempoTotal })
    });
    const data = await res.json();
    if (res.ok) {
      mostrarMensagem(data.status || 'Sucesso!', 'sucesso');
      // Controle UI baseado na ação
      switch (acao) {
        case 'checkin':
          tempoTotal = 0;
          pausado = false;
          iniciarCronometro();
          toggleBotoes({ checkin: true, pausar: false, retomar: true, finalizar: false });
          break;
        case 'pausar':
          pausado = true;
          toggleBotoes({ pausar: true, retomar: false });
          break;
        case 'retomar':
          pausado = false;
          toggleBotoes({ pausar: false, retomar: true });
          break;
        case 'finalizar':
          pausado = true;
          pararCronometro();
          // Exibir relatório se tiver
          if (data.relatorio) {
            document.getElementById('relatorio-box').innerHTML = `
              <h3>Relatório Final:</h3><pre>${data.relatorio}</pre>
            `;
          }
          toggleBotoes({ checkin: false, pausar: true, retomar: true, finalizar: true });
          break;
      }
    } else {
      mostrarMensagem(data.erro || 'Erro inesperado', 'erro');
    }
  } catch {
    mostrarMensagem('Erro ao comunicar com o servidor', 'erro');
  }
}

function toggleBotoes(states) {
  // states: objeto com botão e true=disabled, false=habilitado
  if ('checkin' in states) document.getElementById('checkin').disabled = states.checkin;
  if ('pausar' in states) document.getElementById('pausar').disabled = states.pausar;
  if ('retomar' in states) document.getElementById('retomar').disabled = states.retomar;
  if ('finalizar' in states) document.getElementById('finalizar').disabled = states.finalizar;
}

// Funções atreladas aos botões

function fazerCheckin() { enviarAcao('checkin'); }
function pausar() { enviarAcao('pausar'); }
function retomar() { enviarAcao('retomar'); }
function finalizar() { enviarAcao('finalizar'); }

// --- FUNÇÕES ADMIN ---

async function listarUsuarios() {
  try {
    const res = await fetch('/admin/listar_usuarios');
    if (res.ok) {
      const usuarios = await res.json();
      // Exemplo simples: mostrar lista no console ou em algum container HTML
      console.table(usuarios);
      mostrarMensagem('Lista de usuários carregada', 'sucesso');
    } else {
      mostrarMensagem('Falha ao carregar usuários', 'erro');
    }
  } catch {
    mostrarMensagem('Erro ao comunicar com o servidor', 'erro');
  }
}

async function resetarSessao(nomeUsuario) {
  try {
    const res = await fetch('/admin/resetar_sessao', {
      method: 'POST',
      headers: {'Content-Type': 'application/json'},
      body: JSON.stringify({ nome: nomeUsuario })
    });
    const data = await res.json();
    if (res.ok) {
      mostrarMensagem(data.status || 'Sessão resetada com sucesso', 'sucesso');
    } else {
      mostrarMensagem(data.erro || 'Erro ao resetar sessão', 'erro');
    }
  } catch {
    mostrarMensagem('Erro ao comunicar com o servidor', 'erro');
  }
}

// Expor funções globalmente para o onclick
window.fazerCheckin = fazerCheckin;
window.pausar = pausar;
window.retomar = retomar;
window.finalizar = finalizar;
window.listarUsuarios = listarUsuarios;
window.resetarSessao = resetarSessao;
