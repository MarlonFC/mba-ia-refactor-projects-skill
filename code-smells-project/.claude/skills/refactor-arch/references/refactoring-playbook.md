# Refactoring Playbook — Fase 3

Padrões concretos de transformação. Cada padrão indica os anti-patterns que resolve, exemplos **antes/depois** (Python/Flask e Node/Express — adapte à stack detectada) e como verificar.
Princípio: **mesmo comportamento observável** (ver `mvc-guidelines.md` §5), menos acoplamento.

| ID | Transformação | Resolve |
|---|---|---|
| PB-01 | Externalizar configuração e segredos | AP-01, AP-10 |
| PB-02 | Queries parametrizadas | AP-02 |
| PB-03 | Hash de senha seguro + serialização sem dados sensíveis | AP-03 |
| PB-04 | Proteger endpoints perigosos com token admin | AP-04 |
| PB-05 | Fatiar God Class/Module em Model/Controller/View | AP-05, AP-09 |
| PB-06 | Mover regra de negócio do controller/rota para o model | AP-06 |
| PB-07 | Remover estado global / injetar dependências | AP-07, AP-09 |
| PB-08 | Transação em fluxo multi-escrita | AP-08 |
| PB-09 | Eliminar N+1 e queries redundantes | AP-11, AP-17 |
| PB-10 | Extrair lógica duplicada / reutilizar abstração existente | AP-12 |
| PB-11 | Validação na borda (controller) | AP-13 |
| PB-12 | Error handler central | AP-14 |
| PB-13 | Modernizar APIs deprecated | AP-15 |
| PB-14 | Callbacks aninhados → async/await | AP-06 (callback hell), AP-14 |
| PB-15 | Constantes, nomes, logging e código morto | AP-18–AP-22 |
| PB-16 | Integridade referencial no delete | AP-16 |

---

## PB-01 — Externalizar configuração e segredos

**Antes (Python)**
```python
app = Flask(__name__)
app.config["SECRET_KEY"] = "minha-chave-super-secreta-123"
app.config["DEBUG"] = True
...
app.run(host="0.0.0.0", port=5000, debug=True)
```
**Depois** — `config/settings.py`
```python
import os
import secrets


def _env_bool(name: str, default: bool = False) -> bool:
    return os.getenv(name, str(default)).strip().lower() in {"1", "true", "yes", "on"}


class Settings:
    # Sem segredo literal: usa env ou gera um efêmero (sessões invalidam a cada restart).
    SECRET_KEY = os.getenv("SECRET_KEY") or secrets.token_hex(32)
    DEBUG = _env_bool("APP_DEBUG", False)
    HOST = os.getenv("HOST", "127.0.0.1")
    PORT = int(os.getenv("PORT", "5000"))
    DATABASE_PATH = os.getenv("DATABASE_PATH", "loja.db")
    ADMIN_TOKEN = os.getenv("ADMIN_TOKEN")          # sem default: rotas admin fechadas
    CORS_ORIGINS = os.getenv("CORS_ORIGINS", "*")
```
`app.py`: `app.config.from_object(Settings)` e `app.run(host=Settings.HOST, port=Settings.PORT, debug=Settings.DEBUG)`.

**Antes (Node)**
```js
const config = { dbPass: "senha_super_secreta_prod_123", paymentGatewayKey: "pk_live_123", port: 3000 };
```
**Depois** — `src/config/index.js`
```js
module.exports = Object.freeze({
  port: Number(process.env.PORT) || 3000,
  dbPath: process.env.DB_PATH || ':memory:',
  paymentGatewayKey: process.env.PAYMENT_GATEWAY_KEY || '',
  smtpUser: process.env.SMTP_USER || '',
  adminToken: process.env.ADMIN_TOKEN || '',
});
```
Crie `.env.example` listando as variáveis (sem valores reais). Se o projeto já usa `python-dotenv`/`dotenv`, carregue-o no config; não adicione a dependência só para isso.
**Verificar:** `grep -rnE` dos sinais de AP-01/AP-10 não encontra literais; app sobe sem nenhuma variável definida.

## PB-02 — Queries parametrizadas

**Antes**
```python
cursor.execute("SELECT * FROM usuarios WHERE email = '" + email + "' AND senha = '" + senha + "'")
query += " AND (nome LIKE '%" + termo + "%')"
```
**Depois**
```python
cursor.execute("SELECT * FROM usuarios WHERE email = ?", (email,))

conditions, params = ["1=1"], []
if termo:
    conditions.append("(nome LIKE ? OR descricao LIKE ?)")
    params += [f"%{termo}%", f"%{termo}%"]
cursor.execute(f"SELECT * FROM produtos WHERE {' AND '.join(conditions)}", params)  # só fragmentos fixos interpolados
```
**Node**
```js
// Antes
db.get(`SELECT * FROM users WHERE email = '${email}'`, cb);
// Depois
db.get('SELECT * FROM users WHERE email = ?', [email], cb);
```
**Verificar:** nenhuma string SQL concatenada com variável de input; payload `' OR '1'='1` não altera o resultado.

## PB-03 — Hash de senha seguro + serialização sem dados sensíveis

**Antes**
```python
self.password = hashlib.md5(pwd.encode()).hexdigest()
def to_dict(self): return {"id": self.id, "email": self.email, "password": self.password}
```
**Depois (Python — Werkzeug já vem com Flask)**
```python
from werkzeug.security import check_password_hash, generate_password_hash

def set_password(self, raw: str) -> None:
    self.password = generate_password_hash(raw)

def check_password(self, raw: str) -> bool:
    return check_password_hash(self.password, raw)

def to_dict(self) -> dict:
    return {"id": self.id, "name": self.name, "email": self.email, "role": self.role}  # sem password
```
Dados já gravados no formato antigo (texto plano/MD5): faça **migração transparente** no login — se o valor armazenado não tem prefixo de algoritmo (`scrypt:`/`pbkdf2:`), compare no formato legado com `hmac.compare_digest` e, se bater, regrave com o hash novo. Seeds passam a gravar o hash novo.

**Depois (Node — `crypto` nativo)**
```js
const crypto = require('crypto');

function hashPassword(plain) {
  const salt = crypto.randomBytes(16).toString('hex');
  const hash = crypto.scryptSync(plain, salt, 64).toString('hex');
  return `scrypt$${salt}$${hash}`;
}

function verifyPassword(plain, stored) {
  const [algorithm, salt, hash] = String(stored).split('$');
  if (algorithm !== 'scrypt') return false;
  const candidate = crypto.scryptSync(plain, salt, 64);
  return crypto.timingSafeEqual(candidate, Buffer.from(hash, 'hex'));
}
```
**Logs/respostas:** nunca registrar cartão, senha, token ou chave. Se precisar identificar o cartão: `card.slice(-4)`.
**Verificar:** respostas não contêm `senha/password/secret`; login com credenciais do seed continua funcionando.

## PB-04 — Proteger endpoints perigosos com token admin

**Antes**
```python
@app.route("/admin/query", methods=["POST"])
def executar_query():
    cursor.execute(request.get_json()["sql"])
```
**Depois (Flask)** — `middlewares/auth.py`
```python
import hmac
from functools import wraps
from flask import current_app, request
from middlewares.error_handler import AppError


def require_admin(view):
    @wraps(view)
    def wrapper(*args, **kwargs):
        expected = current_app.config.get("ADMIN_TOKEN")
        provided = request.headers.get("X-Admin-Token", "")
        if not expected or not hmac.compare_digest(provided, expected):
            raise AppError(401, "Não autorizado")
        return view(*args, **kwargs)
    return wrapper
```
**Depois (Express)** — `src/middlewares/auth.js`
```js
const crypto = require('crypto');
const config = require('../config');

module.exports = function requireAdmin(req, res, next) {
  const provided = Buffer.from(req.get('X-Admin-Token') || '');
  const expected = Buffer.from(config.adminToken);
  if (!expected.length || provided.length !== expected.length || !crypto.timingSafeEqual(provided, expected)) {
    return res.status(401).send('Não autorizado');
  }
  next();
};
// router.get('/api/admin/financial-report', requireAdmin, controller.financialReport);
```
Endpoints de execução arbitrária (SQL livre) devem, além do token, ficar restritos a `SELECT` só se o contrato exigir; registre em "Intentional Contract Changes".
**Verificar:** sem header → 401; com `X-Admin-Token: $ADMIN_TOKEN` → status original.

## PB-05 — Fatiar God Class/Module em Model/Controller/View

**Antes** — `AppManager.js` (conexão + schema + rotas + regras na mesma classe)
```js
class AppManager {
  constructor() { this.db = new sqlite3.Database(':memory:'); }
  initDb() { /* CREATE TABLE + seeds */ }
  setupRoutes(app) { app.post('/api/checkout', (req, res) => { /* 50 linhas de regra + SQL */ }); }
}
```
**Depois**
```js
// src/models/courseModel.js
module.exports = (db) => ({
  findActiveById: (id) => db.get('SELECT * FROM courses WHERE id = ? AND active = 1', [id]),
});

// src/controllers/checkoutController.js
module.exports = ({ courseModel, userModel, enrollmentModel }) => ({
  async checkout(input) {
    const course = await courseModel.findActiveById(input.courseId);
    if (!course) throw new AppError(404, 'Curso não encontrado');
    // ... orquestra o caso de uso
  },
});

// src/views/checkoutRoutes.js
module.exports = (controller) => {
  const router = require('express').Router();
  router.post('/api/checkout', asyncHandler(async (req, res) => {
    const result = await controller.checkout(parseCheckoutBody(req.body));
    res.status(200).json({ msg: 'Sucesso', enrollment_id: result.enrollmentId });
  }));
  return router;
};

// src/app.js (composition root)
const db = await openDatabase(config.dbPath);
const controller = createCheckoutController({ courseModel: createCourseModel(db), ... });
app.use(express.json());
app.use(checkoutRoutes(controller));
app.use(errorHandler);
app.listen(config.port);
```
**Python** — `models.py` (4 domínios) → `models/produto_model.py`, `models/usuario_model.py`, `models/pedido_model.py`; `controllers/<dominio>_controller.py`; `views/<dominio>_routes.py` com Blueprint:
```python
# views/produto_routes.py
from flask import Blueprint, jsonify, request
from controllers import produto_controller

produto_bp = Blueprint("produtos", __name__)

@produto_bp.get("/produtos/<int:produto_id>")
def buscar_produto(produto_id):
    return jsonify({"dados": produto_controller.buscar(produto_id), "sucesso": True}), 200

# app.py
def create_app():
    app = Flask(__name__)
    app.config.from_object(Settings)
    init_db(app)
    register_error_handlers(app)
    for bp in (produto_bp, usuario_bp, pedido_bp, relatorio_bp, admin_bp):
        app.register_blueprint(bp)
    return app
```
**Verificar:** paths/métodos idênticos ao inventário; nenhum arquivo mistura SQL com objetos HTTP.

## PB-06 — Mover regra de negócio para o model

**Antes** (regra no controller/rota)
```python
desconto = 0
if faturamento > 10000: desconto = faturamento * 0.1
elif faturamento > 5000: desconto = faturamento * 0.05
```
```js
let status = cc.startsWith("4") ? "PAID" : "DENIED";   // dentro do handler
```
**Depois**
```python
# models/pedido_model.py
DISCOUNT_TIERS = ((10_000, 0.10), (5_000, 0.05), (1_000, 0.02))

def calcular_desconto(faturamento: float) -> float:
    for limite, taxa in DISCOUNT_TIERS:
        if faturamento > limite:
            return faturamento * taxa
    return 0.0
```
```js
// src/models/paymentModel.js (ou services/paymentGateway.js se for integração externa)
const APPROVED_CARD_PREFIX = '4';
const authorize = (cardNumber) => (cardNumber.startsWith(APPROVED_CARD_PREFIX) ? 'PAID' : 'DENIED');
```
Efeitos colaterais (e-mail/SMS/push) → `services/notification_service` chamado pelo controller.
**Verificar:** handler da rota tem só extração de entrada, uma chamada ao controller e serialização.

## PB-07 — Remover estado global / injetar dependências

**Antes**
```python
db_connection = None
def get_db():
    global db_connection
    if db_connection is None:
        db_connection = sqlite3.connect("loja.db", check_same_thread=False)
    return db_connection
```
**Depois** — conexão por contexto de requisição (Flask)
```python
# models/database.py
import sqlite3
from flask import current_app, g


def get_db() -> sqlite3.Connection:
    if "db" not in g:
        g.db = sqlite3.connect(current_app.config["DATABASE_PATH"])
        g.db.row_factory = sqlite3.Row
    return g.db


def close_db(_exc=None) -> None:
    db = g.pop("db", None)
    if db is not None:
        db.close()


def init_db(app) -> None:
    app.teardown_appcontext(close_db)
    with app.app_context():
        create_schema(get_db())
        seed_if_empty(get_db())
```
**Node** — dependências passadas por factory (sem `globalCache` de módulo):
```js
// Antes: let globalCache = {}; function logAndCache(k, v) { globalCache[k] = v; }
// Depois: estado vive em quem o possui e é injetado
const createCheckoutController = ({ enrollmentModel, paymentModel, logger }) => ({ /* ... */ });
```
Caches globais sem leitor real → remover (PB-15). Se o cache for necessário, encapsular com limite (`Map` + tamanho máximo) e injetar.
**Verificar:** `grep -rnE "^\s*global |check_same_thread=False|^let \w+ = \{\}"` vazio.

## PB-08 — Transação em fluxo multi-escrita

**Antes**
```python
for item in itens:
    produto = cursor.execute("SELECT * FROM produtos WHERE id = " + str(item["produto_id"])).fetchone()
    if produto["estoque"] < item["quantidade"]: return {"erro": "Estoque insuficiente"}
cursor.execute("INSERT INTO pedidos ...")
for item in itens:
    cursor.execute("INSERT INTO itens_pedido ...")
    cursor.execute("UPDATE produtos SET estoque = estoque - ...")
db.commit()
```
**Depois (sqlite3: `with conn:` faz commit ou rollback)**
```python
def criar_pedido(db, usuario_id, itens):
    with db:  # transação atômica
        total = 0.0
        cur = db.execute("INSERT INTO pedidos (usuario_id, status, total) VALUES (?, 'pendente', 0)", (usuario_id,))
        pedido_id = cur.lastrowid
        for item in itens:
            produto = db.execute("SELECT nome, preco FROM produtos WHERE id = ?", (item["produto_id"],)).fetchone()
            if produto is None:  # mantém o status que o original usava para este caso (400)
                raise BusinessRuleError(f"Produto {item['produto_id']} não encontrado")
            updated = db.execute(
                "UPDATE produtos SET estoque = estoque - ? WHERE id = ? AND estoque >= ?",
                (item["quantidade"], item["produto_id"], item["quantidade"]),
            )
            if updated.rowcount == 0:  # decremento condicional = sem corrida de estoque
                raise BusinessRuleError(f"Estoque insuficiente para {produto['nome']}")
            db.execute("INSERT INTO itens_pedido (pedido_id, produto_id, quantidade, preco_unitario) VALUES (?, ?, ?, ?)",
                       (pedido_id, item["produto_id"], item["quantidade"], produto["preco"]))
            total += produto["preco"] * item["quantidade"]
        db.execute("UPDATE pedidos SET total = ? WHERE id = ?", (total, pedido_id))
    return {"pedido_id": pedido_id, "total": total}
```
**Node (sqlite3 promisificado — ver PB-14)**
```js
async function withTransaction(db, work) {
  await db.run('BEGIN');
  try { const result = await work(); await db.run('COMMIT'); return result; }
  catch (err) { await db.run('ROLLBACK'); throw err; }
}
```
Com uma única conexão compartilhada no Node, serialize transações (fila/mutex simples) para que requisições concorrentes não intercalem comandos dentro do mesmo `BEGIN`.
**Verificar:** forçar erro no meio (produto inexistente) não deixa pedido/matrícula parcial.

## PB-09 — Eliminar N+1 e queries redundantes

**Antes**
```python
for pedido in pedidos:
    itens = db.execute("SELECT * FROM itens_pedido WHERE pedido_id = " + str(pedido["id"]))
    for item in itens:
        nome = db.execute("SELECT nome FROM produtos WHERE id = " + str(item["produto_id"]))
```
**Depois (1 query + agrupamento em memória)**
```python
rows = db.execute("""
    SELECT p.id, p.usuario_id, p.status, p.total, p.criado_em,
           i.produto_id, i.quantidade, i.preco_unitario, pr.nome AS produto_nome
    FROM pedidos p
    LEFT JOIN itens_pedido i ON i.pedido_id = p.id
    LEFT JOIN produtos pr ON pr.id = i.produto_id
    ORDER BY p.id, i.id
""").fetchall()
pedidos = {}
for r in rows:
    pedido = pedidos.setdefault(r["id"], {"id": r["id"], ..., "itens": []})
    if r["produto_id"] is not None:
        pedido["itens"].append({"produto_id": r["produto_id"],
                                "produto_nome": r["produto_nome"] or "Desconhecido", ...})
return list(pedidos.values())
```
**SQLAlchemy:** `Task.query.options(joinedload(Task.user), joinedload(Task.category)).all()`; contagens por grupo:
```python
counts = dict(db.session.query(Task.status, func.count(Task.id)).group_by(Task.status).all())
pending = counts.get("pending", 0)
```
**Node:** um `SELECT ... JOIN ...` com `db.all` + `reduce` para agrupar por curso, no lugar de `forEach` com `db.get` aninhado.
**Verificar:** mesma resposta JSON (mesma ordem de chaves e itens) com nº de queries constante.

## PB-10 — Extrair lógica duplicada / reutilizar abstração existente

**Antes** (copiado em 6 rotas)
```python
if t.due_date:
    if t.due_date < datetime.utcnow():
        if t.status != 'done' and t.status != 'cancelled':
            task_data['overdue'] = True
        ...
```
**Depois** — usar o método que já existe no model, simplificado:
```python
# models/task.py
def is_overdue(self) -> bool:
    return bool(self.due_date) and self.due_date < utc_now() and self.status not in CLOSED_STATUSES

# controller/view
data = task.to_dict()
data["overdue"] = task.is_overdue()
```
Serialização row→dict repetida → função `_row_to_produto(row)` no model. Constantes já definidas (`VALID_STATUSES`) passam a ser a única fonte; listas literais duplicadas são removidas.
**Verificar:** `grep` da lógica duplicada retorna só a implementação central.

## PB-11 — Validação na borda (controller)

**Antes**
```python
dados = request.get_json()
novo_status = dados.get("status", "")          # body nulo → AttributeError → 500
if priority < 1 or priority > 5: ...           # "3" (string) → TypeError → 500
```
**Depois**
```python
# controllers/validation.py
def require_json(payload) -> dict:
    if not isinstance(payload, dict):
        raise ValidationError("Dados inválidos")
    return payload

def require_int_in_range(value, field, low, high):
    if isinstance(value, bool) or not isinstance(value, int) or not low <= value <= high:
        raise ValidationError(f"{field} deve ser entre {low} e {high}")
    return value
```
```js
// Node
function parseCheckoutBody(body = {}) {
  const { usr, eml, pwd, c_id: courseId, card } = body;
  if (!usr || !eml || !courseId || !card) throw new AppError(400, 'Bad Request');
  return { name: usr, email: eml, password: pwd, courseId: Number(courseId), card: String(card) };
}
```
Mesmas mensagens e status do original para os casos que o original já tratava; casos que davam 500 passam a 400.
**Verificar:** body vazio/tipo errado → 400 (não 500).

## PB-12 — Error handler central

**Antes** (repetido em todo handler)
```python
try:
    ...
except Exception as e:
    return jsonify({"erro": str(e)}), 500
```
**Depois (Flask)** — `middlewares/error_handler.py`
```python
import logging
from flask import jsonify
from werkzeug.exceptions import HTTPException

logger = logging.getLogger(__name__)
ERROR_KEY = "erro"  # mantenha a chave/forma de erro ORIGINAL do projeto ("erro", "error", texto puro…)


class AppError(Exception):
    def __init__(self, status: int, message: str, **extra):
        super().__init__(message)
        self.status, self.message, self.extra = status, message, extra


class ValidationError(AppError):
    def __init__(self, message): super().__init__(400, message)


class NotFoundError(AppError):
    def __init__(self, message): super().__init__(404, message)


def register_error_handlers(app):
    @app.errorhandler(AppError)
    def handle_app_error(err):
        return jsonify({ERROR_KEY: err.message, **err.extra}), err.status

    @app.errorhandler(Exception)
    def handle_unexpected(err):
        if isinstance(err, HTTPException):   # 404/405 do Flask mantêm o comportamento padrão
            return err
        logger.exception("Erro não tratado")
        return jsonify({ERROR_KEY: "Erro interno do servidor"}), 500
```
**Depois (Express 4)** — rejeições de async **não** chegam ao handler sem wrapper:
```js
// src/middlewares/errorHandler.js
class AppError extends Error { constructor(status, message) { super(message); this.status = status; } }
const asyncHandler = (fn) => (req, res, next) => Promise.resolve(fn(req, res, next)).catch(next);

function errorHandler(err, req, res, next) {        // 4 argumentos: registrado por último
  if (err instanceof AppError) return res.status(err.status).send(err.message); // formato original (texto)
  console.error(err);
  return res.status(500).send('Erro interno');
}
module.exports = { AppError, asyncHandler, errorHandler };
```
Remova os `try/except` por rota; mantenha `rollback` onde há transação (PB-08).
**Verificar:** nenhuma rota com `except Exception`/`except:`; erro forçado retorna mensagem genérica e loga a stack.

## PB-13 — Modernizar APIs deprecated

**`datetime.utcnow()`** — manter **naive UTC** para não mudar o formato serializado nem comparar aware × naive com valores lidos do banco:
```python
# Antes
created_at = db.Column(db.DateTime, default=datetime.utcnow)
if t.due_date < datetime.utcnow(): ...
# Depois — utils/time.py (ou models/base)
from datetime import datetime, timezone

def utc_now() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)

created_at = db.Column(db.DateTime, default=utc_now)
```
**`Model.query.get(id)`** (SQLAlchemy 2.x legacy)
```python
# Antes
user = User.query.get(user_id)
# Depois
user = db.session.get(User, user_id)
```
**Node**
```js
new Buffer(data)            →  Buffer.from(data)
url.parse(req.url)          →  new URL(req.url, `http://${req.headers.host}`)
require('body-parser').json() → express.json()
res.send(404)               →  res.sendStatus(404)
```
**Verificar:** rodar com avisos ligados (`python -W error::DeprecationWarning -c "import app"`, `node --throw-deprecation`) e smoke sem warnings novos.

## PB-14 — Callbacks aninhados → async/await

**Antes**
```js
this.db.get(sqlCourse, [cid], (err, course) => {
  this.db.get(sqlUser, [e], (err, user) => {
    this.db.run(sqlEnroll, [uid, cid], function (err) {
      self.db.run(sqlPay, [this.lastID, course.price], function (err) { res.json(...) });
    });
  });
});
```
**Depois** — wrapper promisificado em `src/models/database.js`:
```js
const sqlite3 = require('sqlite3');

function openDatabase(filename) {
  const raw = new sqlite3.Database(filename);
  return {
    run: (sql, params = []) => new Promise((resolve, reject) =>
      raw.run(sql, params, function onRun(err) { err ? reject(err) : resolve({ lastID: this.lastID, changes: this.changes }); })),
    get: (sql, params = []) => new Promise((resolve, reject) => raw.get(sql, params, (err, row) => (err ? reject(err) : resolve(row)))),
    all: (sql, params = []) => new Promise((resolve, reject) => raw.all(sql, params, (err, rows) => (err ? reject(err) : resolve(rows)))),
    exec: (sql) => new Promise((resolve, reject) => raw.exec(sql, (err) => (err ? reject(err) : resolve()))),
  };
}
```
```js
// controller
const course = await courseModel.findActiveById(courseId);
const user = await userModel.findByEmail(email);
const { enrollmentId } = await withTransaction(db, async () => { /* inserts */ });
```
Inicialização assíncrona (schema/seed) deve terminar **antes** de `app.listen`.
**Verificar:** nenhum callback com `(err` ignorado; profundidade de aninhamento ≤ 2.

## PB-15 — Constantes, nomes, logging e código morto

**Antes**
```python
import os, sys, json, datetime            # os/sys/json sem uso
print("Produto criado com ID: " + str(id))
if len(nome) < 2: ...
def is_admin(self):
    if self.role == 'admin':
        return True
    else:
        return False
```
```js
let u = req.body.usr; let cc = req.body.card;
console.log(`[LOG] Salvando no cache: ${key}`);
```
**Depois**
```python
import logging
logger = logging.getLogger(__name__)
MIN_NOME_LENGTH = 2                        # em config/settings.py ou no model do domínio

logger.info("Produto criado com ID %s", produto_id)
if len(nome) < MIN_NOME_LENGTH: ...
def is_admin(self) -> bool:
    return self.role == ROLE_ADMIN
```
```js
const { usr: name, card: cardNumber } = req.body;   // contrato de entrada preservado, nomes internos claros
```
Também: `isinstance(x, list)` em vez de `type(x) == list`; `const` em vez de `let`; remover exports/funções sem referência (`grep -rn nome` = só a definição). Configure o logging uma vez no composition root (`logging.basicConfig(level=...)`).
**Verificar:** linters simples (`python -m pyflakes` se disponível, `node --check`) e grep dos sinais AP-18–AP-22.

## PB-16 — Integridade referencial no delete

**Antes**
```js
db.run("DELETE FROM users WHERE id = ?", [id], (err) => res.send("Usuário deletado, mas as matrículas e pagamentos ficaram sujos no banco."));
```
**Depois**
```js
async deleteUser(id) {
  return withTransaction(db, async () => {
    await db.run('DELETE FROM payments WHERE enrollment_id IN (SELECT id FROM enrollments WHERE user_id = ?)', [id]);
    await db.run('DELETE FROM enrollments WHERE user_id = ?', [id]);
    const { changes } = await db.run('DELETE FROM users WHERE id = ?', [id]);
    return changes > 0;
  });
}
```
```python
# SQLAlchemy: cascade declarado no relacionamento, ou desvincular filhos
category = db.session.get(Category, cat_id)
Task.query.filter_by(category_id=cat_id).update({"category_id": None})
db.session.delete(category)
db.session.commit()
```
Escolha por domínio: filhos que só existem por causa do pai → apagar em cascata na mesma transação; filhos independentes → desvincular (FK = NULL). Mantenha o status/mensagem de sucesso original; registre a decisão no resumo.
**Verificar:** após o delete não há linhas com FK apontando para o registro removido.
