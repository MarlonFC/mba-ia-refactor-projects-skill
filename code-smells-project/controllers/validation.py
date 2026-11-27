from middlewares.error_handler import ValidationError


def require_json(payload) -> dict:
    if not isinstance(payload, dict) or not payload:
        raise ValidationError("Dados inválidos")
    return payload


def require_number(value, message: str) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValidationError(message)
    return value


def require_int(value, message: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int):
        raise ValidationError(message)
    return value


def require_id(value, message: str) -> int:
    """IDs aceitam inteiro ou string numérica (o contrato original aceitava ambos)."""
    if isinstance(value, str) and value.isdigit():
        return int(value)
    return require_int(value, message)


def require_str(value, message: str) -> str:
    if not isinstance(value, str):
        raise ValidationError(message)
    return value


def optional_float(raw: str | None, field: str) -> float | None:
    if not raw:
        return None
    try:
        return float(raw)
    except ValueError:
        raise ValidationError(f"{field} inválido") from None
