# Anti-patterns Catalog — Fase 2

Cada entrada traz: **severidade padrão**, **sinais de detecção** (padrões de grep + critério de confirmação), **não confundir com** (falsos positivos) e o **padrão do playbook** que corrige.
Use os regex com `grep -rnE` (ou a ferramenta Grep) respeitando o escopo de leitura do SKILL.md. Um sinal só vira finding depois de confirmado lendo o trecho.

## Escala de severidade

| Severidade | Quando usar |
|---|---|
| **CRITICAL** | Falha de segurança explorável ou exposição de dados sensíveis (credenciais, senhas, SQL Injection, endpoint destrutivo aberto) ou violação total da separação de responsabilidades (God Class/Module com dados + regras + HTTP). |
| **HIGH** | Violação forte de MVC/SOLID que dificulta manutenção e testes: regra de negócio em controller/rota, acoplamento sem injeção de dependência, estado global mutável, fluxo multi-escrita sem transação, configuração de runtime insegura. |
| **MEDIUM** | Padronização, duplicação, performance moderada: N+1, validação ausente, error handling espalhado, APIs deprecated, integridade referencial. |
| **LOW** | Legibilidade: magic numbers, nomes ruins, logging com print, código morto, construções não idiomáticas. |

Ajuste de severidade só é permitido nos casos descritos em cada entrada ("Escalonamento").

## Índice

| ID | Anti-pattern | Severidade | Playbook |
|---|---|---|---|
| AP-01 | Hardcoded Credentials / Secrets | CRITICAL | PB-01 |
| AP-02 | SQL Injection (query por concatenação) | CRITICAL | PB-02 |
| AP-03 | Insecure Password Storage / Sensitive Data Exposure | CRITICAL | PB-03 |
| AP-04 | Unprotected Dangerous Endpoint | CRITICAL | PB-04 |
| AP-05 | God Class / God Module | CRITICAL | PB-05 |
| AP-06 | Business Logic in Controller/Route (Fat Controller) | HIGH | PB-06, PB-14 |
| AP-07 | Global Mutable State | HIGH | PB-07 |
| AP-08 | Missing Transaction in Multi-write Flow | HIGH | PB-08 |
| AP-09 | Tight Coupling / No Dependency Injection | HIGH | PB-07 |
| AP-10 | Insecure Runtime Configuration | HIGH | PB-01 |
| AP-11 | N+1 Queries | MEDIUM | PB-09 |
| AP-12 | Duplicated Logic / Ignored Existing Abstraction | MEDIUM | PB-10 |
| AP-13 | Missing Input Validation | MEDIUM | PB-11 |
| AP-14 | Scattered or Swallowed Error Handling | MEDIUM | PB-12 |
| AP-15 | Deprecated / Legacy API Usage | MEDIUM | PB-13 |
| AP-16 | Broken Referential Integrity on Delete | MEDIUM | PB-16 |
| AP-17 | Redundant Queries (aggregation in N round-trips) | LOW | PB-09 |
| AP-18 | Magic Numbers / Strings | LOW | PB-15 |
| AP-19 | Poor Naming | LOW | PB-15 |
| AP-20 | Print/Console as Logging | LOW | PB-15 |
| AP-21 | Dead Code / Unused Imports | LOW | PB-15 |
| AP-22 | Non-idiomatic Constructs | LOW | PB-15 |

---

## AP-01 — Hardcoded Credentials / Secrets · CRITICAL

Segredos (chaves, senhas, tokens) escritos no código-fonte ou devolvidos pela API.

**Sinais**
```
(SECRET|secret|PASSWORD|[Pp]ass(word|wd)?|[Tt]oken|API_?KEY|[Kk]ey|[Cc]redential)\w*['"]?\s*[:=]\s*['"][^'"]{3,}['"]
(pk|sk)_(live|test)_[A-Za-z0-9]+
app\.config\[['"]SECRET_KEY['"]\]\s*=\s*['"]
```
Confirme: o valor é literal (não `os.environ`/`process.env`). Inclua também respostas HTTP que devolvem segredos (ex.: `"secret_key": ...` em health check).

**Não confundir com:** placeholders em `.env.example`, valores lidos de env com fallback vazio, nomes de campo em formulários.

## AP-02 — SQL Injection · CRITICAL

SQL montado com dados externos por concatenação/interpolação.

**Sinais**
```
(execute|exec|query|run|get|all|raw)\s*\(\s*["'`].*(SELECT|INSERT|UPDATE|DELETE).*["'`]\s*\+
(SELECT|INSERT|UPDATE|DELETE)[^"']*["']\s*\+\s*\w+
f["'](SELECT|INSERT|UPDATE|DELETE)[^"']*\{
`(SELECT|INSERT|UPDATE|DELETE)[^`]*\$\{
%\s*\(.*\)\s*\)?\s*$   (com string SQL usando %s fora de parâmetro do driver)
```
Também: endpoint que executa SQL recebido do cliente (`execute(dados["sql"])`) → reporte em AP-04 e cite aqui.
Confirme que a variável pode vir de input (request, parâmetro de função pública). Interpolar só constantes internas não é injeção.

**Não confundir com:** placeholders `?`, `%s`, `:name`, `$1` passados como parâmetros separados; ORM (`filter_by`, `.where(col == x)`).

## AP-03 — Insecure Password Storage / Sensitive Data Exposure · CRITICAL

Senha em texto plano, hash fraco (MD5/SHA1 sem salt, base64, "crypto caseiro"), senha/hash devolvidos na API ou dados sensíveis (cartão, chaves) em log.

**Sinais**
```
hashlib\.(md5|sha1)\(|createHash\(['"](md5|sha1)['"]\)
(senha|password|pass|pwd)\s*==|== *\w*(senha|password)
['"](senha|password|pass)['"]\s*:\s*\w+\.(senha|password|pass)      # serialização de senha
Buffer\.from\(.*\)\.toString\(['"]base64['"]\)                       # "hash" via base64
(console\.log|print|logger\.\w+)\(.*(card|cartao|cc|senha|password|token|key)
```
Confirme pelo fluxo: insert/seed com senha crua, comparação direta, `to_dict()`/`SELECT *` devolvendo coluna de senha para o cliente.

## AP-04 — Unprotected Dangerous Endpoint · CRITICAL

Endpoint administrativo, destrutivo ou de execução arbitrária sem autenticação/autorização.

**Sinais**
```
route\(['"]/admin|['"]/api/admin|reset|drop|truncate|/query['"]
\.delete\(['"]|methods=\[['"]DELETE
execute\(\s*(query|sql|dados|data|req\.body)
```
Também: campo de privilégio aceito do cliente (`role`, `is_admin`, `tipo`) em create/update de usuário; token de login previsível/não assinado (`'fake-jwt-token-' + id`).
Confirme: ausência de decorator/middleware de auth na rota e no blueprint/router.
**Escalonamento:** endpoint `DELETE`/`PUT` comum sem auth em API sem nenhum sistema de auth → **HIGH**; `/admin/*`, execução de SQL/código, reset de banco ou dados financeiros/pessoais → sempre **CRITICAL**. A severidade muda só a ordem do relatório — **a correção é obrigatória nos dois casos**.

**Recomendação padrão** (use-a no campo `Recommendation`, listando cada rota do `File:`) — PB-04:
1. **Remover** endpoints que executam SQL/código arbitrário enviado pelo cliente (a rota deixa de existir → `404`). Não basta protegê-los.
2. Exigir token admin (`X-Admin-Token` = `ADMIN_TOKEN` da config, comparação em tempo constante) em **todas** as rotas administrativas, destrutivas (`DELETE`, reset) e de mutação listadas no finding → `401` sem token.
3. Campos de privilégio (`role`, `tipo`, `is_admin`) só são aceitos quando a requisição traz token admin válido; sem ele → `403`.
4. Token de login previsível → token assinado com `SECRET_KEY` (stdlib/framework: `itsdangerous` no Flask, `crypto.createHmac` no Node), mantendo o campo `token` string na resposta.

## AP-05 — God Class / God Module · CRITICAL

Um arquivo/classe concentra responsabilidades de 2+ camadas (acesso a dados + regra de negócio + HTTP/roteamento/serialização) e/ou vários domínios.

**Sinais**
- Arquivo > ~250 linhas com funções de 3+ entidades diferentes (`produto`, `usuario`, `pedido`…).
- Classe com nomes de métodos de camadas distintas: `initDb`/`setupRoutes`/`process*` juntos; `Manager`, `Helper`, `Utils` com estado.
- Mesmo arquivo contém `CREATE TABLE`/SQL **e** `app.get(`/`@route`/`request`/`res.`.
```
class \w*(Manager|Handler|Service|Helper)\b
```
**Escalonamento:** módulo só de dados com 1 domínio grande → HIGH. Cite o intervalo `arquivo:1-N`.

## AP-06 — Business Logic in Controller/Route (Fat Controller) · HIGH

Handler HTTP calcula regras (preço, desconto, estoque, aprovação de pagamento, status), faz queries diretamente, monta agregações ou dispara efeitos colaterais (e-mail/SMS/notificação).

**Sinais**
- Dentro de função de rota: `db.`, `cursor.`, `.query`, `session.`, `SELECT`, cálculos (`*`, `round(`, `sum`), listas literais de valores válidos, loops de agregação.
- Callback aninhado ≥3 níveis em handler (`function(err` dentro de callback dentro de rota) — "callback hell" (JS).
- Efeitos colaterais: `print("ENVIANDO EMAIL`, `send_email(`, `notify` dentro do handler.

**Não confundir com:** validação de formato de entrada (pertence à borda) e chamada única ao model.

## AP-07 — Global Mutable State · HIGH

Variáveis de módulo mutadas em runtime, conexão de banco singleton compartilhada entre requisições/threads, caches globais sem limite.

**Sinais**
```
^\s*global\s+\w+
^(let|var)\s+\w+\s*=\s*(\{\}|\[\]|0|null)        # JS: estado de módulo
check_same_thread\s*=\s*False
^\w+\s*=\s*(None|\{\}|\[\])\s*$                   # Py: estado de módulo mutado depois
```
Confirme que a variável é reatribuída/mutada em funções.

## AP-08 — Missing Transaction in Multi-write Flow · HIGH

Duas ou mais escritas relacionadas (pedido + itens + estoque; matrícula + pagamento + auditoria) sem transação/rollback, ou "check-then-act" de estoque/saldo sem atomicidade.

**Sinais:** mais de um `INSERT/UPDATE/DELETE`/`db.run`/`session.add` no mesmo fluxo sem `BEGIN`/`with conn:`/`session.begin()`/`rollback`; `return` de erro no meio do fluxo após escrita; leitura de estoque seguida de `UPDATE` separado.

## AP-09 — Tight Coupling / No Dependency Injection · HIGH

Camadas instanciam/importam infraestrutura concreta diretamente (conexão global, `new Database()` dentro da classe de domínio, serviço SMTP criado dentro da rota), impossibilitando substituição em testes.

**Sinais:** `from database import get_db` em controllers/rotas; `new sqlite3.Database(` no construtor de classe de negócio; `NotificationService()` instanciado em handler; `import models` + `get_db()` misturados no controller.
**Escalonamento:** reporte junto de AP-05/AP-07 quando for o mesmo trecho (evite finding duplicado).

## AP-10 — Insecure Runtime Configuration · HIGH

Debug ligado fixo, bind em todas as interfaces fixo, CORS aberto, modo produção declarado com debug.

**Sinais**
```
debug\s*=\s*True|\[['"]DEBUG['"]\]\s*=\s*True
host\s*=\s*['"]0\.0\.0\.0['"]
CORS\(app\)\s*$|cors\(\)\s*\)|origin:\s*['"]\*['"]
```
**Escalonamento:** só CORS aberto (sem debug) → MEDIUM.

## AP-11 — N+1 Queries · MEDIUM

Query executada dentro de loop sobre resultado de outra query.

**Sinais:** `for`/`forEach`/`map` contendo `execute(`, `.query`, `.get(`, `db.get(`, `db.all(`, `Model.query.get(`; acesso a relacionamento lazy em loop (`len(u.tasks)` para cada usuário); contagem por item (`.count()` dentro do loop).

## AP-12 — Duplicated Logic / Ignored Existing Abstraction · MEDIUM

Blocos de ≥5 linhas repetidos (serialização row→dict, validações, cálculo de "atrasado"), ou helper/método/constante que já existe e não é usado enquanto a lógica é reescrita inline.

**Sinais:** mesmas sequências de chaves em dicts; mesma lista literal de status em 2+ lugares; função definida em `utils/`/model sem nenhuma referência (`grep -rn "nome_funcao"` só encontra a definição).

## AP-13 — Missing Input Validation · MEDIUM

Dados de request usados sem checar presença, tipo, faixa ou formato; body nulo não tratado; regras de validação diferentes entre create e update.

**Sinais:** `request.get_json()` seguido de `.get(` sem `if not data`; comparação numérica com valor do body sem conversão (`data['priority'] < 1`); `req.body.x` usado sem checagem; ausência de validação de e-mail/enum.
Confirme o efeito (ex.: entrada inválida → 500 em vez de 400).

## AP-14 — Scattered or Swallowed Error Handling · MEDIUM

`try/except` replicado em cada handler, `except:`/`catch {}` genéricos, `err` ignorado em callbacks, `str(e)` devolvido ao cliente, ausência de handler central.

**Sinais**
```
except\s*:                       # bare except
except Exception as e:.*\n.*str\(e\)
\(err(, \w+)*\)\s*=>\s*\{(?![^}]*if\s*\(err)   # callback sem checar err (confirmar lendo)
catch\s*\(\w*\)\s*\{\s*\}
```

## AP-15 — Deprecated / Legacy API Usage · MEDIUM

Uso de API obsoleta, removida ou marcada como legacy na versão da stack detectada. Recomende sempre o equivalente moderno.
**Escalonamento:** API já **removida** na versão instalada (quebra em runtime) → HIGH; aviso apenas estilístico → LOW.

### Tabela de detecção

| Stack | Obsoleto (regex) | Moderno | Observação |
|---|---|---|---|
| Python ≥3.12 | `datetime\.utcnow\(` / `utcfromtimestamp\(` | `datetime.now(timezone.utc)` / `datetime.fromtimestamp(ts, timezone.utc)` | DeprecationWarning desde 3.12. Atenção: comparar aware × naive gera TypeError — normalize. |
| SQLAlchemy 2.x | `\.query\.get\(` | `db.session.get(Model, id)` | `LegacyAPIWarning`. |
| SQLAlchemy 2.x | `\.query\.get_or_404\(` | `db.get_or_404(Model, id)` | Flask-SQLAlchemy ≥3. |
| SQLAlchemy 2.x | `engine\.execute\(` / `session\.execute\(['"]` (string crua) | `conn.execute(text(...))` | removido em 2.0. |
| Flask ≥2.3 | `before_first_request` | inicialização em `create_app()` | removido. |
| Flask ≥2.3 | `json_encoder` / `JSONEncoder` de `flask.json` | `app.json` (`DefaultJSONProvider`) | removido. |
| Flask ≥2.2 | `_app_ctx_stack` / `_request_ctx_stack` | `flask.g`, `current_app` | deprecated. |
| Python | `from collections import (Mapping|Sequence|…)` | `collections.abc` | removido em 3.10. |
| Python | `import imp`, `distutils`, `cgi`, `pkg_resources` | `importlib`, `setuptools`/`packaging`, `email`/libs, `importlib.metadata` | removidos/deprecated. |
| Python | `logging\.warn\(` | `logging.warning(` | deprecated. |
| Node | `new Buffer\(` | `Buffer.from` / `Buffer.alloc` | DEP0005. |
| Node | `url\.parse\(` | `new URL()` | legacy. |
| Node | `crypto\.createCipher\(` | `crypto.createCipheriv` | removido no Node 22. |
| Node | `fs\.exists\(` | `fs.existsSync` / `fs.promises.access` | deprecated. |
| Node | `util\.(isArray|isString|isObject)\(` | `Array.isArray`, `typeof` | deprecated. |
| Node | `require\(['"]querystring['"]\)` | `URLSearchParams` | legacy. |
| Express ≥4.16 | `require\(['"]body-parser['"]\)` | `express.json()` / `express.urlencoded()` | dependência desnecessária. |
| Express 5 | `req\.param\(` , `res\.send\(\d{3}\)`, `res\.json\(\d{3},`, `app\.del\(` | `req.params/query/body`, `res.sendStatus`, `res.status().json()`, `app.delete` | removidos no Express 5. |
| Go | `ioutil\.` | `io` / `os` | deprecated 1.16. |
| PHP | `mysql_\w+\(` | PDO / mysqli | removido no PHP 7. |
| Java | `new (Integer|Long|Double)\(` | `valueOf` | deprecated 9. |

Também verifique dependências declaradas sem versão fixa ou muito antigas e registre avisos de deprecação conhecidos de dependências transitivas apenas como observação (não como finding de código).

## AP-16 — Broken Referential Integrity on Delete · MEDIUM

Remoção de registro pai sem tratar filhos (órfãos), sem FK/cascade, ou resposta de sucesso mesmo quando nada foi removido.

**Sinais:** `DELETE FROM <pai>` sem tratar tabelas que referenciam `<pai>_id`; mensagem que admite inconsistência; `res.send(...)` de sucesso sem checar `this.changes`/`rowcount`; `session.delete(pai)` com filhos via FK sem `cascade`.

## AP-17 — Redundant Queries · LOW

Várias queries de agregação que poderiam ser uma (`COUNT` por status em N chamadas, `SUM` + `COUNT` separados).
**Sinais:** 3+ chamadas `COUNT(*)`/`.count()` consecutivas sobre a mesma tabela com filtros distintos.
**Escalonamento:** dentro de loop → reportar como AP-11.

## AP-18 — Magic Numbers / Strings · LOW

Literais com significado de negócio sem nome: faixas de desconto, limites de tamanho, prioridades, status, porta, prefixo de cartão.
**Sinais:** comparações com literais (`> 10000`, `* 0.1`, `len(x) < 3`, `startsWith("4")`), listas literais de enums repetidas.

## AP-19 — Poor Naming · LOW

Identificadores de 1–2 letras fora de loops curtos (`u`, `e`, `p`, `cc`), nomes que sombreiam builtins (`id`, `type`, `list`), sufixos numéricos (`cursor2`, `cursor3`), nomes enganosos (`badCrypto`, `AppManager`).

## AP-20 — Print/Console as Logging · LOW

`print(`/`console.log(` para eventos da aplicação em vez de logger com níveis. Se o log contém dado sensível, reporte também em AP-03.

## AP-21 — Dead Code / Unused Imports · LOW

Imports, variáveis, funções, classes ou exports nunca usados.
**Sinais:** para cada nome importado, `grep -c` no arquivo = 1; funções sem referências no projeto; `import os, sys, json` sem uso.

## AP-22 — Non-idiomatic Constructs · LOW

`if cond: return True else: return False`; `type(x) == list` (use `isinstance`); `if` aninhados que viram uma expressão; `let` para valores nunca reatribuídos; `self = this` junto com arrow functions; concatenação de strings em vez de f-string/template literal.
