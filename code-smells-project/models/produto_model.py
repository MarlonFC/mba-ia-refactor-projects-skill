"""Acesso a dados e regras do domínio Produto."""
from models.database import get_db

_ATIVO = "ativo = 1"


def listar() -> list[dict]:
    rows = get_db().execute(f"SELECT * FROM produtos WHERE {_ATIVO}").fetchall()
    return [dict(row) for row in rows]


def buscar_por_id(produto_id: int) -> dict | None:
    row = get_db().execute(f"SELECT * FROM produtos WHERE id = ? AND {_ATIVO}", (produto_id,)).fetchone()
    return dict(row) if row else None


def buscar(termo: str, categoria: str | None, preco_min: float | None, preco_max: float | None) -> list[dict]:
    condicoes, params = [_ATIVO], []
    if termo:
        condicoes.append("(nome LIKE ? OR descricao LIKE ?)")
        params += [f"%{termo}%", f"%{termo}%"]
    if categoria:
        condicoes.append("categoria = ?")
        params.append(categoria)
    if preco_min:
        condicoes.append("preco >= ?")
        params.append(preco_min)
    if preco_max:
        condicoes.append("preco <= ?")
        params.append(preco_max)
    # Só fragmentos fixos são interpolados; valores seguem como parâmetros.
    rows = get_db().execute(f"SELECT * FROM produtos WHERE {' AND '.join(condicoes)}", params).fetchall()
    return [dict(row) for row in rows]


def criar(nome: str, descricao: str, preco: float, estoque: int, categoria: str) -> int:
    db = get_db()
    with db:
        cursor = db.execute(
            "INSERT INTO produtos (nome, descricao, preco, estoque, categoria) VALUES (?, ?, ?, ?, ?)",
            (nome, descricao, preco, estoque, categoria),
        )
    return cursor.lastrowid


def atualizar(produto_id: int, nome: str, descricao: str, preco: float, estoque: int, categoria: str) -> None:
    db = get_db()
    with db:
        db.execute(
            "UPDATE produtos SET nome = ?, descricao = ?, preco = ?, estoque = ?, categoria = ? WHERE id = ?",
            (nome, descricao, preco, estoque, categoria, produto_id),
        )


def remover(produto_id: int) -> None:
    """Remove o produto; se já fez parte de pedidos, apenas o desativa para preservar o histórico."""
    db = get_db()
    with db:
        referenciado = db.execute(
            "SELECT 1 FROM itens_pedido WHERE produto_id = ? LIMIT 1", (produto_id,)
        ).fetchone()
        if referenciado:
            db.execute("UPDATE produtos SET ativo = 0 WHERE id = ?", (produto_id,))
        else:
            db.execute("DELETE FROM produtos WHERE id = ?", (produto_id,))
