import os
import sqlite3
from datetime import datetime
from pathlib import Path
from flask import Flask, jsonify, render_template, request

BASE_DIR = Path(__file__).resolve().parent

app = Flask(
    __name__,
    template_folder=str(BASE_DIR / "templates"),
    static_folder=str(BASE_DIR / "static")
)

# =========================================================
# CONFIGURAÇÃO DO BANCO
# =========================================================
DATA_DIR = BASE_DIR / "data"
DATA_DIR.mkdir(parents=True, exist_ok=True)
DATABASE = DATA_DIR / "financeiro.db"

def get_db():
    conn = sqlite3.connect(DATABASE)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn

def init_db():
    conn = get_db()
    conn.executescript(
        """
        CREATE TABLE IF NOT EXISTS meses (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            familia TEXT NOT NULL,
            mes TEXT NOT NULL,
            dinheiro_conta REAL NOT NULL DEFAULT 0,
            reserva_bloqueada REAL NOT NULL DEFAULT 0,
            limite_gasto REAL NOT NULL DEFAULT 150,
            UNIQUE(familia, mes)
        );

        CREATE TABLE IF NOT EXISTS contas (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            mes_id INTEGER NOT NULL,
            nome TEXT NOT NULL,
            valor REAL NOT NULL,
            tipo TEXT NOT NULL CHECK(tipo IN ('fixa', 'variavel')),
            status TEXT NOT NULL DEFAULT 'nao_pago' CHECK(status IN ('pago', 'nao_pago')),
            criado_em TEXT NOT NULL,
            FOREIGN KEY (mes_id) REFERENCES meses(id) ON DELETE CASCADE
        );
        """
    )
    conn.commit()
    conn.close()

def validar_mes(mes):
    try:
        datetime.strptime(mes, "%Y-%m")
        return True
    except (ValueError, TypeError):
        return False

def garantir_mes(familia, mes):
    conn = get_db()
    registro = conn.execute("SELECT * FROM meses WHERE familia = ? AND mes = ?", (familia, mes)).fetchone()
    if registro is None:
        conn.execute(
            """INSERT INTO meses (familia, mes, dinheiro_conta, reserva_bloqueada, limite_gasto) 
               VALUES (?, ?, 0, 0, 150)""", (familia, mes)
        )
        conn.commit()
        registro = conn.execute("SELECT * FROM meses WHERE familia = ? AND mes = ?", (familia, mes)).fetchone()
    conn.close()
    return registro

def obter_dashboard(familia, mes):
    garantir_mes(familia, mes)
    conn = get_db()
    mes_db = conn.execute("SELECT * FROM meses WHERE familia = ? AND mes = ?", (familia, mes)).fetchone()
    contas = conn.execute(
        """SELECT * FROM contas WHERE mes_id = ? 
           ORDER BY CASE WHEN status = 'nao_pago' THEN 0 ELSE 1 END, id DESC""",
        (mes_db["id"],)
    ).fetchall()
    
    total_contas = sum(conta["valor"] for conta in contas)
    total_pago = sum(conta["valor"] for conta in contas if conta["status"] == "pago")
    total_nao_pago = sum(conta["valor"] for conta in contas if conta["status"] == "nao_pago")
    restante_previsto = mes_db["dinheiro_conta"] - total_contas
    disponivel_apos_reserva = restante_previsto - mes_db["reserva_bloqueada"]
    limite_gasto = mes_db["limite_gasto"]

    if disponivel_apos_reserva <= 0:
        aviso = "Atenção: não há dinheiro livre disponível depois das contas e da reserva."
        nivel_aviso = "perigo"
    elif disponivel_apos_reserva < limite_gasto:
        aviso = "Atenção: o valor disponível está abaixo do limite de gasto configurado."
        nivel_aviso = "atencao"
    else:
        aviso = f"Você pode gastar no máximo R$ {limite_gasto:.2f} do valor disponível."
        nivel_aviso = "seguro"

    resultado = {
        "mes": mes_db["mes"],
        "familia": mes_db["familia"],
        "dinheiro_conta": mes_db["dinheiro_conta"],
        "reserva_bloqueada": mes_db["reserva_bloqueada"],
        "limite_gasto": limite_gasto,
        "total_contas": total_contas,
        "total_pago": total_pago,
        "total_nao_pago": total_nao_pago,
        "restante_previsto": restante_previsto,
        "disponivel_apos_reserva": disponivel_apos_reserva,
        "aviso": aviso,
        "nivel_aviso": nivel_aviso,
        "contas": [dict(conta) for conta in contas],
    }
    conn.close()
    return resultado

# =========================================================
# ROTAS E APIS
# =========================================================

@app.route("/")
def home():
    return render_template("index.html")

@app.route("/api/dashboard", methods=["GET"])
def dashboard():
    mes = request.args.get("mes", datetime.now().strftime("%Y-%m"))
    familia = str(request.args.get("familia", "FamiliaSilva")).strip().lower()
    
    if not validar_mes(mes):
        return jsonify({"erro": "Mês inválido."}), 400
    return jsonify(obter_dashboard(familia, mes))

@app.route("/api/meses/<mes>/configuracoes", methods=["PUT"])
def atualizar_configuracoes(mes):
    if not validar_mes(mes):
        return jsonify({"erro": "Mês inválido."}), 400
    
    dados = request.get_json() or {}
    familia = str(dados.get("familia", "FamiliaSilva")).strip().lower()
    garantir_mes(familia, mes)

    try:
        dinheiro_conta = float(dados.get("dinheiro_conta", 0))
        reserva_bloqueada = float(dados.get("reserva_bloqueada", 0))
        limite_gasto = float(dados.get("limite_gasto", 150))
    except (ValueError, TypeError):
        return jsonify({"erro": "Valores inválidos."}), 400

    conn = get_db()
    conn.execute(
        """UPDATE meses SET dinheiro_conta = ?, reserva_bloqueada = ?, limite_gasto = ?
           WHERE familia = ? AND mes = ?""",
        (dinheiro_conta, reserva_bloqueada, limite_gasto, familia, mes)
    )
    conn.commit()
    conn.close()
    return jsonify(obter_dashboard(familia, mes))

@app.route("/api/contas", methods=["POST"])
def criar_conta():
    dados = request.get_json() or {}
    mes = dados.get("mes")
    familia = str(dados.get("familia", "FamiliaSilva")).strip().lower()
    nome = str(dados.get("nome", "")).strip()
    tipo = dados.get("tipo", "variavel")

    if not validar_mes(mes) or not nome:
        return jsonify({"erro": "Mês ou nome inválido."}), 400

    try:
        valor = float(dados.get("valor", 0))
        if valor <= 0: raise ValueError
    except (ValueError, TypeError):
        return jsonify({"erro": "Valor inválido."}), 400

    mes_db = garantir_mes(familia, mes)
    conn = get_db()
    conn.execute(
        """INSERT INTO contas (mes_id, nome, valor, tipo, status, criado_em)
           VALUES (?, ?, ?, ?, 'nao_pago', ?)""",
        (mes_db["id"], nome, valor, tipo, datetime.now().isoformat())
    )
    conn.commit()
    conn.close()
    return jsonify(obter_dashboard(familia, mes)), 201

@app.route("/api/contas/<int:conta_id>/status", methods=["PATCH"])
def alterar_status(conta_id):
    dados = request.get_json() or {}
    status = dados.get("status")
    
    conn = get_db()
    conta = conn.execute("SELECT contas.*, meses.mes, meses.familia FROM contas JOIN meses ON meses.id = contas.mes_id WHERE contas.id = ?", (conta_id,)).fetchone()
    
    if not conta or status not in ["pago", "nao_pago"]:
        conn.close()
        return jsonify({"erro": "Operação inválida."}), 400

    conn.execute("UPDATE contas SET status = ? WHERE id = ?", (status, conta_id))
    conn.commit()
    conn.close()
    return jsonify(obter_dashboard(conta["familia"], conta["mes"]))

@app.route("/api/contas/<int:conta_id>", methods=["DELETE"])
def excluir_conta(conta_id):
    conn = get_db()
    conta = conn.execute("SELECT contas.*, meses.mes, meses.familia FROM contas JOIN meses ON meses.id = contas.mes_id WHERE contas.id = ?", (conta_id,)).fetchone()
    
    if not conta:
        conn.close()
        return jsonify({"erro": "Conta não encontrada."}), 404

    conn.execute("DELETE FROM contas WHERE id = ?", (conta_id,))
    conn.commit()
    conn.close()
    return jsonify(obter_dashboard(conta["familia"], conta["mes"]))

@app.route("/api/meses/<mes>/copiar-fixas", methods=["POST"])
def copiar_contas_fixas(mes):
    familia = str(request.args.get("familia", "FamiliaSilva")).strip().lower()
    if not validar_mes(mes):
        return jsonify({"erro": "Mês inválido."}), 400

    mes_atual = garantir_mes(familia, mes)
    conn = get_db()
    mes_anterior = conn.execute(
        "SELECT * FROM meses WHERE familia = ? AND mes < ? ORDER BY mes DESC LIMIT 1", (familia, mes)
    ).fetchone()

    if not mes_anterior:
        conn.close()
        return jsonify({"erro": "Não existe mês anterior."}), 404

    contas_fixas = conn.execute("SELECT * FROM contas WHERE mes_id = ? AND tipo = 'fixa'", (mes_anterior["id"],)).fetchall()
    copiadas = 0

    for conta in contas_fixas:
        existe = conn.execute(
            "SELECT id FROM contas WHERE mes_id = ? AND LOWER(nome) = LOWER(?) AND tipo = 'fixa'",
            (mes_atual["id"], conta["nome"])
        ).fetchone()

        if not existe:
            conn.execute(
                "INSERT INTO contas (mes_id, nome, valor, tipo, status, criado_em) VALUES (?, ?, ?, 'fixa', 'nao_pago', ?)",
                (mes_atual["id"], conta["nome"], conta["valor"], datetime.now().isoformat())
            )
            copiadas += 1

    conn.commit()
    conn.close()
    
    resposta = obter_dashboard(familia, mes)
    resposta["contas_copiadas"] = copiadas
    return jsonify(resposta)

@app.route("/health", methods=["GET"])
def health():
    return jsonify({"status": "ok"})

init_db()

if __name__ == "__main__":
    port = int(os.getenv("PORT", 8000))
    app.run(host="0.0.0.0", port=port, debug=False)
