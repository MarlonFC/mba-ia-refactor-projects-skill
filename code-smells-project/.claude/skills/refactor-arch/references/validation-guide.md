# Validation Guide — Fase 3

A validação compara o comportamento HTTP **antes** e **depois** da refatoração com o script `scripts/smoke.sh` (bash + curl, agnóstico de stack). Artefatos ficam em `.refactor-arch/`.

`SKILL_DIR` = diretório deste skill (ex.: `.claude/skills/refactor-arch`).

## 1. Preparar o ambiente

| Stack | Dependências | Interpretador |
|---|---|---|
| Python | Se existir `.venv/` ou `venv/`, use-o. Senão: `python3 -m venv .venv && .venv/bin/pip install -q -r requirements.txt` | `.venv/bin/python` |
| Node | Se não existir `node_modules/`: `npm install --no-audit --no-fund` | `node` / `npm start` |

Não altere manifestos para validar. Se faltar uma dependência que o código já importa, registre no resumo.

## 2. Estado de dados reprodutível

O baseline e o "after" precisam partir do **mesmo estado inicial**:

- **Banco em arquivo** (ex.: `loja.db`, `instance/tasks.db`): se existir, **mova** para `.refactor-arch/db-backup/` (nunca apague). Antes de cada execução, garanta que o arquivo não existe para a app recriá-lo; rode o passo de seed se o projeto tiver um (ex.: `python seed.py`).
- **Banco em memória**: nada a fazer (reinicia a cada boot).
- Ao final (§6), restaure o backup para o caminho original.

## 3. Gerar `requests.txt` e o baseline

Formato — uma requisição por linha; `#` comenta; JSON opcional após o path:
```
# METHOD PATH [JSON]
GET /produtos
GET /produtos/999
POST /produtos {"nome":"Livro X","preco":10.5,"estoque":3,"categoria":"livros"}
PUT /pedidos/1/status {"status":"aprovado"}
```

Regras para montar a lista (a partir do inventário de rotas da Fase 1):
1. **Toda rota** aparece ao menos uma vez com um caso de sucesso, usando IDs que existem após o seed.
2. Rotas com validação ou busca por ID ganham **um caso de erro** (ID inexistente, campo obrigatório ausente).
3. Ordem: leituras → criações → atualizações → deleções → rotas destrutivas globais (reset) **por último**. Delete preferencialmente de um registro criado na própria lista.
4. Valores coerentes com o seed (leia o seed/código; não invente campos).
5. Inclua os exemplos de `.http`/README do projeto, se existirem.

Execução:
```bash
# terminal da validação (exemplo Python; adapte comando/porta do perfil de execução)
export ADMIN_TOKEN=refactor-arch-validation        # inofensivo para o código original
<comando de start> > .refactor-arch/app-before.log 2>&1 &
APP_PID=$!
for i in $(seq 1 60); do curl -s -o /dev/null http://localhost:<porta>/ && break; sleep 0.5; done
bash "$SKILL_DIR/scripts/smoke.sh" http://localhost:<porta> .refactor-arch/requests.txt .refactor-arch/baseline.txt \
     "X-Admin-Token: $ADMIN_TOKEN"
kill $APP_PID; wait $APP_PID 2>/dev/null
```
- Para apps sem rota `/`, faça o *wait* em uma rota GET do inventário (qualquer resposta HTTP serve; `000` = ainda não subiu).
- Se a porta estiver ocupada, pare o processo que você mesmo iniciou ou use `PORT` alternativa nas duas execuções.
- O header admin é enviado em todas as requisições; o código original o ignora, o refatorado o exige nas rotas admin → status iguais.

## 4. Validar o código refatorado

1. Mesmo estado de dados (§2) e mesmo **comando de start** do baseline (o entry point original deve continuar funcionando).
2. Boot: o log não pode conter traceback/stack trace; a primeira requisição deve responder.
3. Rodar o smoke → `.refactor-arch/after.txt` (log da app em `app-after.log`).
4. Comparar:
```bash
diff .refactor-arch/baseline.txt .refactor-arch/after.txt && echo "STATUS MATCH"
```
   `smoke.sh` grava `STATUS METHOD PATH` por linha e os corpos em `<arquivo>.bodies`.
5. Corpos: confira em `*.bodies` que as respostas de sucesso mantêm as mesmas chaves de topo e tipos. Diferenças aceitas só as de `mvc-guidelines.md` §5 (ex.: campo `senha` removido).

**Regras de aceite**
- Status idênticos para todas as linhas, exceto mudanças permitidas e listadas em "Intentional Contract Changes".
- Nenhum `000` (conexão recusada) nem `500` novo.
- Se falhar: leia `app-after.log`, corrija, repita §4 (até 3 ciclos). Persistindo, reporte `✗` com o motivo — nunca esconda falha.

## 5. Re-auditoria

Re-aplique os sinais do catálogo sobre os arquivos novos:
- **CRITICAL/HIGH**: devem ser zero. Se sobrar algum, corrija antes de concluir. Única exceção: findings cuja correção exige mudança de contrato **não** permitida em `mvc-guidelines.md` §5 (ex.: criar autenticação para rotas comuns) — marque como `deferred (requer mudança de contrato: <qual>)` e liste-os na linha de validação.
- **MEDIUM/LOW** remanescentes: liste em "Findings Resolution" como `partially resolved`/`not resolved` com o motivo.
- Rode verificação de deprecações quando possível (`python -W error::DeprecationWarning -c "import app"` após preparar o banco; `node --throw-deprecation` no boot).

## 6. Encerramento

1. Garanta que nenhum processo iniciado pela skill continua rodando (`kill` dos PIDs).
2. Restaure backups de banco de `.refactor-arch/db-backup/` para os caminhos originais.
3. Remova arquivos gerados pela validação fora de `.refactor-arch/` (ex.: banco recriado que não existia antes).
4. Mantenha `.refactor-arch/` com: `audit-report.md`, `requests.txt`, `baseline.txt(.bodies)`, `after.txt(.bodies)`, `app-before.log`, `app-after.log`.
