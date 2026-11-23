# Project Analysis — heurísticas da Fase 1

Objetivo: descobrir **o que** é o projeto (stack, domínio), **como** ele está organizado e **como** executá-lo — sem executar nada.

## 1. Inventário de arquivos

```bash
find . -type f \
  -not -path './.git/*' -not -path './.claude/*' -not -path './.refactor-arch/*' \
  -not -path '*/node_modules/*' -not -path '*/.venv/*' -not -path '*/venv/*' -not -path '*/env/*' \
  -not -path '*/vendor/*' -not -path '*/__pycache__/*' -not -path '*/dist/*' -not -path '*/build/*' \
  -not -path '*/instance/*' -not -name '*.lock' -not -name 'package-lock.json' \
  -not -name '*.db' -not -name '*.sqlite*' -not -name '*.pyc'
```

- **Source files** = arquivos de código da linguagem principal (`.py`, `.js`, `.ts`, `.go`, `.java`, `.rb`, `.php`, …). Não conte README, `.http`, manifestos nem `__init__.py` vazios (1 linha ou menos) — mas mencione-os se forem relevantes.
- **LOC** = soma de `wc -l` dos source files.

## 2. Linguagem (pelo manifesto, confirmada pelas extensões)

| Manifesto / arquivo | Linguagem | Onde ler versão |
|---|---|---|
| `requirements.txt`, `pyproject.toml`, `Pipfile`, `setup.py` | Python | `python_requires`, `.python-version`, `runtime.txt` |
| `package.json` | JavaScript (TypeScript se houver `tsconfig.json` ou `.ts`) | `engines.node`, `.nvmrc` |
| `go.mod` | Go | diretiva `go` |
| `pom.xml`, `build.gradle(.kts)` | Java/Kotlin | `maven.compiler.source`, `sourceCompatibility` |
| `Gemfile` | Ruby | `ruby` no Gemfile |
| `composer.json` | PHP | `require.php` |
| `*.csproj` | C# | `TargetFramework` |

Sem manifesto: use a extensão predominante.

## 3. Framework (pelas dependências, confirmado por imports)

| Dependência | Framework | Sinal no código |
|---|---|---|
| `flask` | Flask | `Flask(__name__)`, `@app.route`, `Blueprint(` |
| `fastapi` | FastAPI | `FastAPI()`, `@app.get` |
| `django` | Django | `urls.py`, `INSTALLED_APPS` |
| `express` | Express | `require('express')` / `import express`, `app.get(` |
| `fastify`, `koa`, `@nestjs/core` | Fastify / Koa / NestJS | `fastify(`, `new Koa()`, `@Controller(` |
| `gin-gonic/gin`, `labstack/echo` | Gin / Echo | `gin.Default()`, `echo.New()` |
| `spring-boot-starter-web` | Spring Boot | `@RestController` |
| `rails`, `sinatra` | Rails / Sinatra | `config/routes.rb`, `get '/'` |
| `laravel/framework` | Laravel | `routes/web.php`, `Route::get` |

Versão: use a do manifesto (`flask==3.1.1`, `"express": "^4.18.2"` → `4.18.2 (^)`).
**Dependencies** no resumo: liste extensões e libs relevantes (CORS, ORM, driver de banco, validação, dotenv), não o framework novamente.

## 4. Banco de dados

| Sinal | Banco / acesso |
|---|---|
| `import sqlite3`, `sqlite3.connect(`, `require('sqlite3')`, `better-sqlite3`, `:memory:` | SQLite (raw SQL) |
| `flask_sqlalchemy`, `sqlalchemy`, `SQLALCHEMY_DATABASE_URI` | SQLAlchemy ORM (dialeto pela URI) |
| `psycopg`, `pg`, `postgres://` | PostgreSQL |
| `pymysql`, `mysql2`, `mysql://` | MySQL |
| `mongoose`, `pymongo` | MongoDB |
| `sequelize`, `typeorm`, `prisma`, `knex` | ORM/Query builder Node |

**Tabelas:** `grep -rn "CREATE TABLE"`; `__tablename__ = '...'`; classes `db.Model`/`Base`; `sequelize.define(`; `schema.prisma`. Se não houver nome explícito, use o nome da classe do model.

**Arquivo de banco:** caminho na connect string (`loja.db`, `sqlite:///tasks.db` → Flask-SQLAlchemy ≥3 cria em `instance/tasks.db`), ou `:memory:` (sem arquivo).

## 5. Inventário de rotas (contrato da Fase 3)

| Framework | Padrões de grep |
|---|---|
| Flask | `@\w+\.route\(`, `\.add_url_rule\(`, `\.(get|post|put|patch|delete)\(` em blueprints; prefixo em `register_blueprint(..., url_prefix=` e `Blueprint(..., url_prefix=` |
| FastAPI | `@\w+\.(get|post|put|patch|delete)\(`, `include_router(..., prefix=` |
| Express/Koa/Fastify | `\b(app|router|\w+Router)\.(get|post|put|patch|delete|all)\(`, `app.use\('/prefix', router` |
| Django | `path\(`, `re_path\(` em `urls.py` |
| Spring | `@(Get|Post|Put|Patch|Delete|Request)Mapping` |
| Go | `HandleFunc\(`, `\.(GET|POST|PUT|PATCH|DELETE)\(` |

Para cada rota registre: método, path completo (com prefixos), handler, `arquivo:linha`, parâmetros de path/query, se recebe JSON e quais campos lê. Flask: métodos ausentes em `@route` = `GET`.

## 6. Perfil de execução

| Stack | Entry point | Comando de start | Porta |
|---|---|---|---|
| Flask | arquivo com `app.run(` ou `if __name__ == '__main__'`; ou `create_app` | `python <arquivo>` (ou o descrito no README) | argumento `port=` (padrão 5000) |
| FastAPI | `uvicorn.run(` | `uvicorn mod:app` | padrão 8000 |
| Express | `main` / `scripts.start` do `package.json`; arquivo com `.listen(` | `npm start` | argumento de `.listen(` / `process.env.PORT` |

Também registre: passo de **seed/migração** (`seed.py`, `migrations/`, `npm run seed`, README "rode antes"), variáveis de ambiente lidas (`os.environ`, `os.getenv`, `process.env`) e **instruções do README** do projeto (fonte primária para o comando de start).

## 7. Domínio

Infira pelos nomes de tabelas, rotas e entidades (ex.: `produtos/pedidos/usuarios` → "E-commerce API"; `courses/enrollments/payments` + `/checkout` → "LMS com checkout"; `tasks/categories/users` → "Task Manager"). Descreva em uma linha com as entidades principais entre parênteses.

## 8. Classificação da arquitetura

| Classificação | Critérios |
|---|---|
| **Monolítica** | ≤ ~5 arquivos concentram rotas, regras e SQL; existe arquivo/classe com responsabilidades de 2+ camadas (ex.: SQL + regra + HTTP); sem pastas por camada. |
| **Parcialmente em camadas** | Existem pastas como `models/`, `routes/`, `services/`, `utils/`, mas pelo menos uma camada faz o trabalho de outra (ex.: rotas com regra de negócio e queries; helpers não usados; falta controller/config/error handler). |
| **Em camadas (MVC ou similar)** | Rotas só mapeiam HTTP → controller; controllers orquestram; models encapsulam dados/regras; config e tratamento de erros centralizados. |

Inclua na linha `Architecture:` a justificativa curta (ex.: "Monolítica — 4 arquivos, SQL e regras no mesmo módulo, sem camadas").

Também anote para a Fase 3: quais camadas **já existem e estão adequadas** (devem ser preservadas), quais faltam e quais estão no lugar errado.
