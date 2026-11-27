from models.database import get_db


def contagens() -> dict:
    db = get_db()
    return {
        "produtos": db.execute("SELECT COUNT(*) FROM produtos").fetchone()[0],
        "usuarios": db.execute("SELECT COUNT(*) FROM usuarios").fetchone()[0],
        "pedidos": db.execute("SELECT COUNT(*) FROM pedidos").fetchone()[0],
    }


def resetar_banco() -> None:
    db = get_db()
    with db:
        for tabela in ("itens_pedido", "pedidos", "produtos", "usuarios"):
            db.execute(f"DELETE FROM {tabela}")  # nomes fixos, sem input externo
