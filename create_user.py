# create_user.py - versão com senha em texto puro (para uso pessoal)
import sqlite3

DB_NAME = 'ponto.db'

def criar_usuario(username, senha):
    try:
        with sqlite3.connect(DB_NAME) as conn:
            c = conn.cursor()
            c.execute('INSERT INTO usuarios (username, senha_hash) VALUES (?, ?)', (username, senha))
            conn.commit()
            print(f"Usuário '{username}' criado com sucesso!")
    except sqlite3.IntegrityError:
        print(f"Erro: o usuário '{username}' já existe.")

if __name__ == '__main__':
    print("=== Criar novo usuário (senha em texto simples) ===")
    username = input("Nome de usuário: ")
    senha = input("Senha: ")
    criar_usuario(username, senha)
