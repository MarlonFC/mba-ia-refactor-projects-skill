# ecommerce-api-legacy

LMS API (com fluxo de checkout) em Node.js/Express usada como entrada do desafio `refactor-arch`.

## Como rodar

```bash
npm install
npm start
```

A aplicação sobe em `http://localhost:3000`. O banco SQLite é em memória e já carrega seeds automaticamente no boot.

Variáveis de ambiente (ver `.env.example`): `PORT` (padrão 3000) e `ADMIN_TOKEN` — exigido no header `X-Admin-Token` das rotas `/api/admin/*`; sem ele configurado essas rotas respondem 401.

Exemplos de requisições estão em `api.http`.
