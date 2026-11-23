"""Casos de uso de Produto: validação de entrada e orquestração do model."""
import logging

from config.settings import CATEGORIA_PADRAO, CATEGORIAS_VALIDAS, NOME_PRODUTO_MAX, NOME_PRODUTO_MIN
from controllers.validation import eh_numero, exigir_objeto
from middlewares.error_handler import NotFoundError, ValidationError
from models import produto_model

logger = logging.getLogger(__name__)

_OBRIGATORIOS = (("nome", "Nome é obrigatório"), ("preco", "Preço é obrigatório"), ("estoque", "Estoque é obrigatório"))


def _validar(dados, *, criacao: bool) -> tuple:
    """Regras de entrada do produto. Tamanho do nome e categoria só são checados na criação (contrato original)."""
    dados = exigir_objeto(dados)
    for campo, mensagem in _OBRIGATORIOS:
        if campo not in dados:
            raise ValidationError(mensagem)

    nome, preco, estoque = dados["nome"], dados["preco"], dados["estoque"]
    descricao = dados.get("descricao", "")
    categoria = dados.get("categoria", CATEGORIA_PADRAO)

    if not isinstance(nome, str):
        raise ValidationError("Nome inválido")
    if not isinstance(descricao, str):
        raise ValidationError("Descrição inválida")
    if not eh_numero(preco):
        raise ValidationError("Preço inválido")
    if not eh_numero(estoque):
        raise ValidationError("Estoque inválido")
    if preco < 0:
        raise ValidationError("Preço não pode ser negativo")
    if estoque < 0:
        raise ValidationError("Estoque não pode ser negativo")

    if criacao:
        if len(nome) < NOME_PRODUTO_MIN:
            raise ValidationError("Nome muito curto")
        if len(nome) > NOME_PRODUTO_MAX:
            raise ValidationError("Nome muito longo")
        if categoria not in CATEGORIAS_VALIDAS:
            raise ValidationError(f"Categoria inválida. Válidas: {CATEGORIAS_VALIDAS}")
    elif not isinstance(categoria, str):
        raise ValidationError("Categoria inválida")

    return nome, descricao, preco, estoque, categoria


def listar() -> list[dict]:
    produtos = produto_model.listar()
    logger.info("Listando %d produtos", len(produtos))
    return produtos


def obter(produto_id: int) -> dict:
    produto = produto_model.buscar_por_id(produto_id)
    if produto is None:
        raise NotFoundError("Produto não encontrado", sucesso=False)
    return produto


def _preco_filtro(valor: str | None, campo: str) -> float | None:
    if not valor:
        return None
    try:
        return float(valor)
    except ValueError:
        raise ValidationError(f"{campo} inválido") from None


def buscar(termo: str, categoria: str | None, preco_min: str | None, preco_max: str | None) -> list[dict]:
    return produto_model.buscar(
        termo, categoria, _preco_filtro(preco_min, "preco_min"), _preco_filtro(preco_max, "preco_max")
    )


def criar(dados) -> int:
    produto_id = produto_model.criar(*_validar(dados, criacao=True))
    logger.info("Produto criado com ID %s", produto_id)
    return produto_id


def atualizar(produto_id: int, dados) -> None:
    if produto_model.buscar_por_id(produto_id) is None:
        raise NotFoundError("Produto não encontrado")
    produto_model.atualizar(produto_id, *_validar(dados, criacao=False))


def remover(produto_id: int) -> None:
    if produto_model.buscar_por_id(produto_id) is None:
        raise NotFoundError("Produto não encontrado")
    produto_model.remover(produto_id)
    logger.info("Produto %s removido", produto_id)
