"""Validações de entrada reutilizadas pelos controllers."""
from middlewares.error_handler import ValidationError


def exigir_objeto(payload, *, aceita_vazio: bool = False) -> dict:
    if not isinstance(payload, dict) or (not payload and not aceita_vazio):
        raise ValidationError("Dados inválidos")
    return payload


def eh_numero(valor) -> bool:
    return isinstance(valor, (int, float)) and not isinstance(valor, bool)


def como_inteiro(valor) -> int | None:
    """Aceita int ou string de dígitos (o contrato original aceitava ambos); senão None."""
    if isinstance(valor, int) and not isinstance(valor, bool):
        return valor
    if isinstance(valor, str) and valor.isdigit():
        return int(valor)
    return None


def textos_preenchidos(*valores) -> bool:
    return all(isinstance(valor, str) and valor for valor in valores)
