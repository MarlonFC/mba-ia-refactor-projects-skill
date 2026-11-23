# Audit Report Template — Fase 2

Imprima o relatório **exatamente** nesta estrutura. Rótulos em inglês; textos em português do Brasil.

## Regras

1. **Ordem:** CRITICAL → HIGH → MEDIUM → LOW; dentro da severidade, por arquivo e linha.
2. **Numeração:** `F-01`, `F-02`, … contínua na ordem final (a Fase 3 referencia esses IDs).
3. **`File:`** sempre `caminho/relativo:linha` ou `:inicio-fim`. Várias ocorrências → separe por `, ` (ex.: `models.py:28, 47-50, 92`). Arquivos diferentes → `; `. Nunca use "várias linhas" ou "~".
4. **Um finding por problema-causa.** Não divida o mesmo anti-pattern em findings por linha; não junte anti-patterns diferentes.
5. **`Anti-pattern:`** referencia o ID do catálogo (`AP-xx`).
6. **APIs deprecated** aparecem como findings normais (AP-15) com o equivalente moderno na recomendação. Se não houver nenhuma, escreva a linha `Deprecated APIs: none detected for <stack>` no bloco de resumo.
7. O **Summary** deve bater com a contagem real; `Total` = soma.
8. Nada de "..." ou "etc." — o relatório é completo.

## Estrutura

```
================================
ARCHITECTURE AUDIT REPORT
================================
Project: <nome da pasta do projeto>
Stack:   <Linguagem> + <Framework versão> (<banco>)
Files:   <N> analyzed | ~<LOC> lines of code

## Summary
CRITICAL: <n> | HIGH: <n> | MEDIUM: <n> | LOW: <n>
Deprecated APIs: <n detected (F-xx, F-yy) | none detected for <stack>>

## Findings

### F-01 [CRITICAL] <Título do anti-pattern>
Anti-pattern: AP-xx
File: <arquivo:linhas>
Description: <o que acontece, citando o trecho/identificador concreto>
Impact: <consequência concreta: o que um atacante/usuário/mantenedor sofre>
Recommendation: <correção específica + padrão PB-xx>

### F-02 [HIGH] ...
(repita para todos)

================================
Total: <N> findings
================================
```

## Exemplo preenchido (formato de referência)

```
### F-01 [CRITICAL] SQL Injection
Anti-pattern: AP-02
File: models.py:28, 47-50, 109-111
Description: Queries montadas por concatenação com valores do request (ex.: "SELECT * FROM usuarios WHERE email = '" + email + "'").
Impact: Login sem senha com email "admin@loja.com' --"; leitura e alteração arbitrária do banco.
Recommendation: Usar parâmetros do driver ("WHERE email = ?", (email,)) em todas as queries (PB-02).

### F-07 [MEDIUM] Deprecated API: datetime.utcnow()
Anti-pattern: AP-15
File: models/task.py:15-16, 52; routes/task_routes.py:31, 72
Description: datetime.utcnow() está deprecated desde o Python 3.12 e emite DeprecationWarning.
Impact: Remoção futura quebrará o código; retorna datetime naive, sujeito a erros de fuso.
Recommendation: Substituir por datetime.now(timezone.utc) centralizado em um helper utc_now() (PB-13).
```
