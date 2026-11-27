from werkzeug.security import check_password_hash, generate_password_hash

from models.database import get_db

TIPO_PADRAO = "cliente"


def _usuario_to_dict(row) -> dict:
    # Nunca serializa a coluna senha.
    return {
        "id": row["id"],
        "nome": row["nome"],
        "email": row["email"],
        "tipo": row["tipo"],
        "criado_em": row["criado_em"],
    }


def listar() -> list[dict]:
    rows = get_db().execute("SELECT * FROM usuarios").fetchall()
    return [_usuario_to_dict(row) for row in rows]


def buscar_por_id(usuario_id: int) -> dict | None:
    row = get_db().execute("SELECT * FROM usuarios WHERE id = ?", (usuario_id,)).fetchone()
    return _usuario_to_dict(row) if row else None


def autenticar(email: str, senha: str) -> dict | None:
    row = get_db().execute("SELECT * FROM usuarios WHERE email = ?", (email,)).fetchone()
    if row is None or not row["senha"] or not check_password_hash(row["senha"], senha):
        return None
    return {"id": row["id"], "nome": row["nome"], "email": row["email"], "tipo": row["tipo"]}


def criar(nome: str, email: str, senha: str, tipo: str = TIPO_PADRAO) -> int:
    db = get_db()
    with db:
        cursor = db.execute(
            "INSERT INTO usuarios (nome, email, senha, tipo) VALUES (?, ?, ?, ?)",
            (nome, email, generate_password_hash(senha), tipo),
        )
    return cursor.lastrowid
