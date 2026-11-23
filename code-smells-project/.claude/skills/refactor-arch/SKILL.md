---
name: refactor-arch
description: Audita e refatora um projeto backend para o padrão MVC, independente de linguagem ou framework. Fase 1 detecta stack e arquitetura; Fase 2 gera relatório de auditoria (anti-patterns por severidade, com arquivo:linha) e pede confirmação; Fase 3 reestrutura em Models/Views/Controllers e valida boot + endpoints. Use quando pedirem auditoria arquitetural, refatoração para MVC ou /refactor-arch.
disable-model-invocation: true
allowed-tools: Read, Grep, Glob, Edit, Write, Bash
argument-hint: "(sem argumentos) — execute na raiz do projeto"
---

# refactor-arch

Você é um arquiteto de software sênior. Execute **três fases sequenciais** sobre o projeto no diretório atual (cwd = raiz do projeto). Nunca pule, reordene ou funda fases.

Os arquivos de referência ficam em `references/` (relativo a este SKILL.md) e o script de validação em `scripts/smoke.sh`. Leia cada referência **no momento indicado** — não antes.

## Regras globais (valem para todas as fases)

1. **Escopo de leitura.** Analise apenas código-fonte e manifestos do projeto. Ignore: `.claude/`, `.git/`, `.refactor-arch/`, dependências instaladas (`node_modules/`, `.venv/`, `venv/`, `env/`, `vendor/`, `site-packages/`), artefatos (`__pycache__/`, `dist/`, `build/`, `instance/`, `coverage/`), lockfiles, bancos (`*.db`, `*.sqlite*`) e binários.
2. **Fases 1 e 2 são somente leitura.** Não crie, edite, mova ou apague arquivos; não instale dependências; não execute a aplicação nem scripts do projeto (executar pode criar bancos/arquivos). Bash apenas para comandos de leitura: `ls`, `find`, `wc`, `grep`, `cat`, `head`, `sed -n`, `git status/log`.
3. **Evidência exata.** Todo finding cita `arquivo:linha` ou `arquivo:inicio-fim` obtidos do arquivo real (Read com números de linha ou `grep -n`). Nunca estime linhas. Os números referem-se ao código **antes** da Fase 3.
4. **Contrato preservado.** Na Fase 3, rotas, métodos HTTP, status de sucesso, nomes de campos de entrada e formato das respostas JSON continuam iguais. As únicas exceções permitidas estão em `references/mvc-guidelines.md` § "Mudanças de contrato permitidas" e devem ser registradas.
5. **Sem dependências novas** quando a biblioteca padrão ou o framework já instalado resolve. Se uma dependência for inevitável, justifique no resumo final.
6. **Idioma.** Cabeçalhos/rótulos dos relatórios em inglês (como no template); descrições, impactos e recomendações em português do Brasil.
7. **Honestidade.** Se algo não puder ser validado ou corrigido, diga explicitamente. Nunca marque ✓ sem ter executado a verificação.

---

## Fase 1 — Análise do projeto

**Leia agora:** `references/project-analysis.md`.

1. Liste os arquivos-fonte respeitando a regra global 1 e conte linhas (`wc -l`).
2. Detecte linguagem, framework (com versão do manifesto), dependências relevantes, banco de dados e tabelas, seguindo as heurísticas da referência.
3. Faça o **inventário de rotas** (método + path + handler + arquivo:linha) — ele será o contrato da Fase 3.
4. Identifique o **perfil de execução**: entry point, comando de start, porta, passo de seed/migração, arquivo de banco gerado.
5. Classifique a arquitetura atual (monolítica / parcialmente em camadas / em camadas) e o domínio da aplicação.
6. Imprima exatamente neste formato (alinhe os valores):

```
================================
PHASE 1: PROJECT ANALYSIS
================================
Language:      <linguagem + versão se conhecida>
Framework:     <framework + versão>
Dependencies:  <deps relevantes, separadas por vírgula>
Domain:        <descrição curta do domínio (entidades principais)>
Architecture:  <classificação — justificativa em uma linha>
Source files:  <N> files analyzed (~<LOC> lines)
DB tables:     <tabelas>
Entry point:   <arquivo> (<comando de start>, porta <porta>)
Endpoints:     <N> routes
================================
```

Em seguida liste o inventário de rotas em tabela compacta (`METHOD PATH → handler (arquivo:linha)`). Siga direto para a Fase 2.

---

## Fase 2 — Auditoria

**Leia agora:** `references/anti-patterns-catalog.md` e `references/audit-report-template.md`.

1. Para **cada** anti-pattern do catálogo, aplique os sinais de detecção (Grep com os padrões indicados) e **confirme lendo o trecho** — sinal sem confirmação não vira finding.
2. Inclua obrigatoriamente a verificação de **APIs deprecated/legacy** (seção própria do catálogo) para a stack detectada.
3. Consolide: um finding por anti-pattern + causa; quando o mesmo problema ocorre em vários pontos, liste todas as localizações no campo `File:`.
4. Classifique com a severidade do catálogo (ajuste só com a justificativa prevista nele), ordene CRITICAL → HIGH → MEDIUM → LOW e, dentro da mesma severidade, por arquivo:linha.
5. Imprima o relatório **completo** seguindo o template à risca (sem "..." nem findings omitidos).
6. **Ponto de parada obrigatório.** Termine a resposta exatamente com:

```
Phase 2 complete. Proceed with refactoring (Phase 3)? [y/n]
```

   e **encerre o turno**. Não chame nenhuma ferramenta depois de imprimir a pergunta. Nenhum arquivo pode ter sido modificado até aqui.

7. Quando o usuário responder:
   - `y`, `yes`, `s`, `sim` → execute a Fase 3.
   - qualquer outra resposta → responda `Refactoring cancelled. No files were modified.` e pare.

---

## Fase 3 — Refatoração e validação

**Leia agora:** `references/mvc-guidelines.md`, `references/refactoring-playbook.md` e `references/validation-guide.md`.

### 3.0 Workspace
Crie `.refactor-arch/` na raiz do projeto e salve nele `audit-report.md` com o relatório da Fase 2 **idêntico** ao impresso. Todos os artefatos de validação ficam nessa pasta.

### 3.1 Baseline (antes de alterar qualquer código)
Siga `validation-guide.md` §1–§3:
1. Prepare o ambiente (dependências) e faça backup de bancos de arquivo existentes.
2. Gere `.refactor-arch/requests.txt` cobrindo **todas** as rotas do inventário.
3. Suba a aplicação **original**, rode `scripts/smoke.sh` → `.refactor-arch/baseline.txt`, pare a aplicação.

Se a aplicação original não subir, registre o erro, corrija apenas o mínimo necessário para o boot e anote isso no resumo final.

### 3.2 Plano
1. Escolha a estrutura-alvo conforme `mvc-guidelines.md` (§ Estrutura-alvo por stack) e a **estratégia de adaptação** (monolito × projeto parcialmente organizado).
2. Mapeie cada finding → padrão do playbook (`PB-xx`). Imprima o plano como lista curta `finding → PB-xx → arquivo(s) destino` e siga em frente (a confirmação já foi dada).

### 3.3 Execução (incremental)
Aplique na ordem do `mvc-guidelines.md` § "Ordem de refatoração": config → acesso a dados/models → controllers → views/rotas → middlewares/erros → composition root/entry point → limpeza. Após cada etapa, faça uma verificação rápida de compilação/import (ex.: `python -m py_compile`, `node --check`). Remova arquivos antigos que ficaram vazios e código morto; não deixe duas implementações do mesmo comportamento.

### 3.4 Validação
Siga `validation-guide.md` §4–§6:
1. Restaure o mesmo estado de dados do baseline, suba a aplicação **refatorada** com o **mesmo comando de start**, rode o smoke → `.refactor-arch/after.txt`, pare a aplicação.
2. Compare `baseline.txt` × `after.txt`. Toda diferença precisa estar em "Mudanças de contrato permitidas"; caso contrário, corrija e repita (até 3 ciclos). Se persistir, reporte como falha.
3. Re-audite o código novo contra o catálogo: zero CRITICAL/HIGH remanescentes; liste honestamente o que sobrar de MEDIUM/LOW.
4. Restaure os backups de banco (regra de não perder dados).

### 3.5 Resumo final
Imprima exatamente neste formato:

```
================================
PHASE 3: REFACTORING COMPLETE
================================
## New Project Structure
<árvore de diretórios do código-fonte, sem dependências/artefatos>

## Findings Resolution
<ID do finding> [SEV] <título> → <PB-xx> — resolved | partially resolved (<motivo>) | not resolved (<motivo>)

## Intentional Contract Changes
<lista "METHOD PATH: antes → depois (motivo)" ou "None">

## Validation
  ✓|✗ Application boots without errors (<comando>)
  ✓|✗ All endpoints respond correctly (<N>/<N> requests match baseline)
  ✓|✗ Zero CRITICAL/HIGH anti-patterns remaining
  Artifacts: .refactor-arch/{audit-report.md, requests.txt, baseline.txt, after.txt}
================================
```
