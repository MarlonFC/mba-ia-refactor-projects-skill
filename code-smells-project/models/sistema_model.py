"""Operações de infraestrutura/administração sobre o banco."""
import sqlite3

from models.database import get_db

_TABELAS_RESET = ("itens_pedido", "pedidos", "produtos", "usuarios")  # filhos antes dos pais


def contagens() -> dict:
    row = get_db().execute(
        """
        SELECT (SELECT COUNT(*) FROM produtos WHERE ativo = 1) AS produtos,
               (SELECT COUNT(*) FROM usuarios) AS usuarios,
               (SELECT COUNT(*) FROM pedidos) AS pedidos
        """
    ).fetchone()
    return dict(row)


def resetar() -> None:
    db = get_db()
    with db:
        for tabela in _TABELAS_RESET:
            db.execute(f"DELETE FROM {tabela}")  # nomes fixos, sem entrada externa


class QueryInvalidaError(Exception):
    """SQL administrativo rejeitado pelo banco."""


def executar_sql(sql: str) -> list[dict] | None:
    """Executa SQL administrativo. Retorna as linhas para SELECT e None para comandos de escrita."""
    db = get_db()
    try:
        with db:
            cursor = db.execute(sql)
            if sql.strip().upper().startswith("SELECT"):
                return [dict(row) for row in cursor.fetchall()]
    except sqlite3.Error as err:
        raise QueryInvalidaError(str(err)) from err
    return None
