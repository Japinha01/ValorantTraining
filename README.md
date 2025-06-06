# Sistema de Check-in com Notificações via Telegram

Este é um sistema de check-in online feito em Flask, com armazenamento via SQLite e envio de notificações para o Telegram. Você pode rodar localmente ou com Docker.

---

## ✅ Funcionalidades

* Login de usuários com senha segura
* Check-in com registro de data/hora
* Notificações automáticas para o Telegram
* Interface via navegador (HTML/CSS)

---

## 🚀 Rodando com Docker (recomendado)

### 1. Instale o Docker

* [Download do Docker Desktop](https://www.docker.com/products/docker-desktop/)

### 2. Crie o arquivo `Dockerfile`

Crie um arquivo chamado `Dockerfile` (sem extensão) com o seguinte conteúdo:

```dockerfile
FROM python:3.11-slim

WORKDIR /app

COPY . /app

RUN pip install --no-cache-dir flask werkzeug requests

EXPOSE 5000

ENV FLASK_APP=app.py
ENV FLASK_RUN_HOST=0.0.0.0

CMD ["flask", "run"]
```

### 3. Construa a imagem

```bash
docker build -t sistema-checkin .
```

### 4. Rode o container

```bash
docker run -d -p 5000:5000 --name checkin \
  -e TELEGRAM_TOKEN=seu_token \
  -e TELEGRAM_CHAT_ID=seu_chat_id \
  sistema-checkin
```

Substitua `seu_token` e `seu_chat_id` com os dados do seu bot Telegram.

### 5. Acesse o sistema

Abra o navegador em: [http://localhost:5000](http://localhost:5000)

---

## 💻 Rodando localmente (sem Docker)

### 1. Instale as dependências

```bash
pip install flask werkzeug requests
```

### 2. Rode o sistema

```bash
python app.py
```

### 3. Acesse o sistema

[http://localhost:5000](http://localhost:5000)

---

## 👤 Criando usuários

Use o script `create_user.py` para adicionar novos usuários:

```bash
python create_user.py
```

Digite o nome de usuário e senha quando solicitado. O sistema usa senha criptografada.

---

## 📦 Estrutura

```
/ (raiz)
├── app.py             # Sistema principal
├── create_user.py     # Script para criar usuários
├── ponto.db           # Banco de dados SQLite
├── templates/         # HTMLs (login.html, index.html, etc)
├── Dockerfile         # Instruções para criar imagem Docker
```

---

## 📬 Notificações Telegram

Para usar:

1. Crie um bot com o [BotFather](https://t.me/botfather)
2. Obtenha o `TELEGRAM_TOKEN`
3. Adicione o bot ao seu grupo/canal
4. Pegue o `chat_id` (pode usar o [@userinfobot](https://t.me/userinfobot) ou outros meios)

As mensagens de check-in são enviadas automaticamente para esse chat.

---

## 🛑 Parar o container

```bash
docker stop checkin
```

## 🗑 Remover o container

```bash
docker rm checkin
```

---

Sistema feito com 💻 + ☕ + ❤️
