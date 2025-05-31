import sqlite3

conn = sqlite3.connect('ponto.db')
c = conn.cursor()

c.execute("SELECT id, username FROM usuarios")
usuarios = c.fetchall()

print("Usuários cadastrados:")
for usuario in usuarios:
    print(f"ID: {usuario[0]} | Nome: {usuario[1]}")

conn.close()
