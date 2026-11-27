# task-manager-api

API de Task Manager em Python/Flask, refatorada para MVC pela skill `refactor-arch` (relatório em `.refactor-arch/audit-report.md`).

## Como rodar

```bash
pip install -r requirements.txt
cp .env.example .env   # ajuste SECRET_KEY e ADMIN_TOKEN
python seed.py
python app.py
```

A aplicação sobe em `http://127.0.0.1:5000` (configure `HOST`/`PORT`). O `seed.py` popula o banco SQLite (`instance/tasks.db`) com usuários, categorias e tasks de exemplo; **rode-o antes do primeiro boot**.

## Configuração (variáveis de ambiente / `.env`)

| Variável | Padrão | Uso |
|---|---|---|
| `SECRET_KEY` | aleatório por processo | Assina os tokens de login |
| `ADMIN_TOKEN` | — (rotas admin fechadas) | Valor esperado no header `X-Admin-Token` |
| `DATABASE_URL` | `sqlite:///tasks.db` | URI do SQLAlchemy |
| `APP_DEBUG` | `false` | Modo debug do Flask |
| `HOST` / `PORT` | `127.0.0.1` / `5000` | Bind do servidor |
| `CORS_ORIGINS` | vazio | Origens liberadas no CORS (separadas por vírgula) |

## Autorização

- `DELETE /tasks/<id>`, `DELETE /users/<id>` e `DELETE /categories/<id>` exigem `X-Admin-Token`; sem o header válido a resposta é `401`.
- Em `POST /users`, um `role` diferente de `user` exige `X-Admin-Token`; sem ele a resposta é `403`. Em `PUT /users/<id>`, enviar `role` ou `active` também exige o token (`403`).
- `POST /login` devolve em `token` um token assinado com `SECRET_KEY`.

```bash
curl -X DELETE http://127.0.0.1:5000/tasks/1 -H "X-Admin-Token: $ADMIN_TOKEN"
```

## Estrutura

```
app.py                 # composition root: create_app(), registra blueprints e error handlers
config/settings.py     # Settings (env) + constantes de domínio
database.py            # instância SQLAlchemy
models/                # ORM + regras de domínio (task, user, category) e agregações (report)
controllers/           # casos de uso + validação de entrada
routes/                # camada View: blueprints finos (HTTP → controller → JSON)
middlewares/           # error_handler (AppError → JSON) e auth (X-Admin-Token, token de login)
utils/                 # utc_now, calculate_percentage, validate_email
seed.py                # dados iniciais
```
