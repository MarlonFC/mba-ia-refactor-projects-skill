"""Acesso a dados e regras do domínio Usuário (a senha nunca sai deste módulo)."""
import hmac

from werkzeug.security import check_password_hash, generate_password_hash

from config.settings import TIPO_USUARIO_PADRAO
from models.database import get_db

_CAMPOS_PUBLICOS = "id, nome, email, tipo, criado_em"
_PREFIXOS_HASH = ("scrypt:", "pbkdf2:")


def listar() -> list[dict]:
    rows = get_db().execute(f"SELECT {_CAMPOS_PUBLICOS} FROM usuarios").fetchall()
    return [dict(row) for row in rows]


def buscar_por_id(usuario_id: int) -> dict | None:
    row = get_db().execute(f"SELECT {_CAMPOS_PUBLICOS} FROM usuarios WHERE id = ?", (usuario_id,)).fetchone()
    return dict(row) if row else None


def criar(nome: str, email: str, senha: str, tipo: str = TIPO_USUARIO_PADRAO) -> int:
    db = get_db()
    with db:
        cursor = db.execute(
            "INSERT INTO usuarios (nome, email, senha, tipo) VALUES (?, ?, ?, ?)",
            (nome, email, generate_password_hash(senha), tipo),
        )
    return cursor.lastrowid


def _senha_confere(armazenada: str | None, senha: str) -> bool:
    if not armazenada:
        return False
    if armazenada.startswith(_PREFIXOS_HASH):
        return check_password_hash(armazenada, senha)
    # Registro legado em texto plano: compara em tempo constante.
    return hmac.compare_digest(armazenada.encode(), senha.encode())


def autenticar(email: str, senha: str) -> dict | None:
    db = get_db()
    rows = db.execute("SELECT id, nome, email, tipo, senha FROM usuarios WHERE email = ?", (email,)).fetchall()
    for row in rows:
        if _senha_confere(row["senha"], senha):
            if not row["senha"].startswith(_PREFIXOS_HASH):
                # Migração transparente do legado para hash.
                with db:
                    db.execute(
                        "UPDATE usuarios SET senha = ? WHERE id = ?", (generate_password_hash(senha), row["id"])
                    )
            return {"id": row["id"], "nome": row["nome"], "email": row["email"], "tipo": row["tipo"]}
    return None
