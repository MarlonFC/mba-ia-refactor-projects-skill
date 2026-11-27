================================
ARCHITECTURE AUDIT REPORT
================================
Project: ecommerce-api-legacy
Stack:   JavaScript + Express 4.18.2 (SQLite in-memory via sqlite3)
Files:   3 analyzed | ~180 lines of code

## Summary
CRITICAL: 4 | HIGH: 3 | MEDIUM: 4 | LOW: 5
Deprecated APIs: none detected for Node.js 22 / Express 4

## Findings

### F-01 [CRITICAL] Hardcoded Credentials / Secrets
Anti-pattern: AP-01
File: src/utils.js:1-7
Description: O objeto `config` traz segredos literais no código: `dbUser: "admin_master"`, `dbPass: "senha_super_secreta_prod_123"`, `paymentGatewayKey: "pk_live_1234567890abcdef"` e `smtpUser`, além da porta fixa `3000`.
Impact: Qualquer pessoa com acesso ao repositório obtém a chave live do gateway de pagamento e a senha de banco de produção. Trocar uma credencial exige alterar o código e fazer novo deploy.
Recommendation: (1) Criar `src/config/index.js` que lê `PAYMENT_GATEWAY_KEY`, `ADMIN_TOKEN` e `PORT` de `process.env` (com padrão `3000` só para a porta). (2) Remover de `src/utils.js` os literais `dbUser`, `dbPass` e `smtpUser`, que não são usados, e o literal `paymentGatewayKey`. (3) Criar `.env.example` só com placeholders (PB-01).

### F-02 [CRITICAL] Insecure Password Storage / Sensitive Data Exposure
Anti-pattern: AP-03
File: src/AppManager.js:18, 45, 68; src/utils.js:17-23
Description: `badCrypto()` só repete os 2 primeiros caracteres do base64 da senha e trunca em 10 (é reversível e não tem salt). O seed grava a senha `'123'` em texto puro. O checkout faz `console.log` do número completo do cartão (`cc`) junto com `config.paymentGatewayKey`. Quando `pwd` não vem no body, o código usa a senha padrão `"123456"`.
Impact: Quem vazar o banco recupera prefixos de senha de forma trivial, e senhas diferentes geram o mesmo "hash". Os logs passam a conter PAN de cartão e a chave do gateway, o que viola o PCI-DSS. Contas criadas sem senha ficam com uma senha conhecida.
Recommendation: (1) Trocar `badCrypto` por `crypto.scryptSync` com salt aleatório por usuário (formato `salt:hash`, só stdlib). (2) Gravar o seed (src/AppManager.js:18) com hash. (3) Tirar do log da linha 45 o cartão e a chave, deixando no máximo os 4 últimos dígitos mascarados. (4) Eliminar a senha padrão `"123456"` (linha 68): sem `pwd`, gravar `pass` como `NULL` (PB-03).

### F-03 [CRITICAL] Unprotected Dangerous Endpoint
Anti-pattern: AP-04
File: src/AppManager.js:80-129, 131-137
Description: `GET /api/admin/financial-report` expõe a receita por curso e o nome e o valor pago por aluno, e `DELETE /api/users/:id` apaga usuários. Nenhuma das duas rotas tem autenticação.
Impact: Um cliente anônimo lê dados financeiros e pessoais de todos os alunos e apaga qualquer usuário enumerando ids.
Recommendation: Exigir o header `X-Admin-Token` igual a `ADMIN_TOKEN` da config, com comparação em tempo constante (`crypto.timingSafeEqual`), por meio de um middleware `requireAdmin` em (1) `GET /api/admin/financial-report` e (2) `DELETE /api/users/:id`. Sem token ou com token inválido a resposta é `401` (PB-04).

### F-04 [CRITICAL] God Class (com acoplamento sem DI)
Anti-pattern: AP-05 (+AP-09 no mesmo trecho)
File: src/AppManager.js:1-141
Description: A classe `AppManager` cria a conexão (`new sqlite3.Database(':memory:')`, linha 7), define schema e seed (`initDb`, 10-23), registra as rotas HTTP e contém as regras de checkout, pagamento e relatório (`setupRoutes`, 25-138) para 4 entidades.
Impact: Não dá para testar regra de negócio sem subir HTTP e um banco concreto. Qualquer mudança mexe no mesmo arquivo, e não é possível trocar o banco nem injetar um mock.
Recommendation: Desmembrar em: `src/config/`, `src/models/` (database.js com conexão e schema/seed; um model por tabela: user, course, enrollment, payment, auditLog), `src/services/` (checkoutService, reportService), `src/controllers/`, `src/routes/`, `src/middlewares/` (auth, errorHandler) e `src/app.js` como composition root. O composition root cria a conexão e a injeta nos models e services via factories. Apagar `src/AppManager.js` (PB-05, PB-07).

### F-05 [HIGH] Business Logic in Route Handlers (callback hell)
Anti-pattern: AP-06
File: src/AppManager.js:28-78, 80-129
Description: O handler de checkout busca o curso, cria o usuário, decide a aprovação do pagamento (`cc.startsWith("4")`) e grava matrícula, pagamento e auditoria em 6 níveis de callbacks aninhados. O handler do relatório agrega a receita com contadores manuais (`coursesPending`/`enrPending`).
Impact: Regras de pagamento e de faturamento ficam presas ao HTTP, não são testáveis e são frágeis (as contagens manuais ficam penduradas se algum callback falhar).
Recommendation: (1) Mover o fluxo de checkout (resolver/criar usuário, aprovar pagamento, matricular, auditar) para `checkoutService.checkout()` com async/await. (2) Mover a agregação do relatório para `reportService.financialReport()`. Os handlers de `POST /api/checkout` e `GET /api/admin/financial-report` passam a só ler a request, chamar o service e responder (PB-06, PB-14).

### F-06 [HIGH] Global Mutable State
Anti-pattern: AP-07
File: src/utils.js:9-15, 25; src/AppManager.js:2, 59
Description: `globalCache` é um objeto de módulo que `logAndCache` muta a cada checkout, sem limite e sem nenhuma leitura. `totalRevenue` é um `let` de módulo exportado e importado.
Impact: Vazamento de memória que cresce com cada usuário que faz checkout, e estado compartilhado invisível entre requisições, que fica inconsistente com múltiplas instâncias.
Recommendation: (1) Remover `globalCache`, `logAndCache` e `totalRevenue` de `src/utils.js`. (2) Remover a chamada em src/AppManager.js:59 e o import da linha 2. Nenhum estado de request fica em variável de módulo (PB-07).

### F-07 [HIGH] Missing Transaction in Multi-write Flow
Anti-pattern: AP-08
File: src/AppManager.js:50-61, 69-72
Description: O checkout faz até 4 escritas encadeadas (INSERT users, enrollments, payments, audit_logs) sem `BEGIN/COMMIT`. Se uma escrita falhar no meio, as anteriores continuam gravadas.
Impact: Podem surgir matrículas sem pagamento (acesso ao curso sem cobrança) ou usuários criados com checkout recusado ou falho, e o estado financeiro fica inconsistente.
Recommendation: Executar criação de usuário + matrícula + pagamento + auditoria dentro de uma transação única (`BEGIN` … `COMMIT`, `ROLLBACK` em qualquer erro) em `checkoutService`. A decisão de pagamento acontece antes de qualquer escrita (PB-08).

### F-08 [MEDIUM] N+1 Queries
Anti-pattern: AP-11
File: src/AppManager.js:89-127
Description: Para cada curso há um `SELECT` de enrollments (linha 92), e para cada matrícula mais um `SELECT` de users (104) e outro de payments (106).
Impact: O número de queries cresce em 1 + C + 2·E, e o relatório fica lento à medida que as matrículas aumentam.
Recommendation: Uma única query com `LEFT JOIN` entre courses, enrollments, users e payments, agrupada no service mantendo a mesma ordem e o mesmo formato (PB-09).

### F-09 [MEDIUM] Missing Input Validation
Anti-pattern: AP-13
File: src/AppManager.js:29-35, 132
Description: O checkout só verifica se os campos são truthy: não confere se `card` é string, se `c_id` é inteiro nem se `eml` tem formato de e-mail. O `:id` do DELETE não é validado.
Impact: `card` numérico (ex.: `4111…` sem aspas) faz `cc.startsWith` lançar TypeError dentro do callback do sqlite. Isso derruba o processo inteiro (DoS com uma única requisição).
Recommendation: Validar na borda que `usr`/`eml`/`card` são strings não vazias, `eml` tem formato de e-mail e `c_id`/`:id` são inteiros positivos, respondendo `400` com a mesma mensagem `Bad Request` (PB-11).

### F-10 [MEDIUM] Scattered or Swallowed Error Handling
Anti-pattern: AP-14
File: src/AppManager.js:38, 57, 92-93, 104, 106, 133-135
Description: Os erros de callback são ignorados (auditoria na 57, users/payments na 104/106, DELETE na 133). Na 92-93, um `err` causa `enrollments.length` sobre undefined. Na 38, um erro de banco vira `404`. Não existe handler central.
Impact: Falhas de banco viram crash do processo ou respostas enganosas (sucesso ou 404), e não há tratamento padronizado.
Recommendation: Usar promises (async/await) nos models, propagar erros via `next(err)` e ter um middleware `errorHandler` central que responde `500` sem detalhes internos (PB-12).

### F-11 [MEDIUM] Broken Referential Integrity on Delete
Anti-pattern: AP-16
File: src/AppManager.js:131-137
Description: `DELETE FROM users` não trata as matrículas e os pagamentos do usuário (a própria mensagem admite que "ficaram sujos no banco") e responde sucesso mesmo quando o id não existe (não verifica `this.changes`).
Impact: Ficam registros órfãos, e o cliente recebe confirmação falsa de exclusão de usuário inexistente.
Recommendation: Verificar `changes` e responder `404` quando nada foi removido. Tratar os dependentes de forma explícita: preservar matrículas e pagamentos como histórico financeiro (o relatório já mostra o aluno como `Unknown`) e registrar a exclusão em `audit_logs` (PB-16).

### F-12 [LOW] Magic Numbers / Strings
Anti-pattern: AP-18
File: src/AppManager.js:21, 46, 48, 68, 108; src/utils.js:6, 18
Description: O prefixo de cartão `"4"`, os status `'PAID'`/`'DENIED'` repetidos, a senha padrão `"123456"`, a porta `3000` e as `10000` iterações aparecem como literais.
Impact: A regra de aprovação e os status ficam espalhados, e é fácil divergir em mudanças.
Recommendation: Constantes nomeadas (`PAYMENT_STATUS`, `APPROVED_CARD_PREFIX`) no model/service, com a porta vinda da config (PB-15).

### F-13 [LOW] Poor Naming
Anti-pattern: AP-19
File: src/AppManager.js:4, 26, 29-33; src/utils.js:17
Description: Variáveis `u`, `e`, `p`, `cid`, `cc`, classe genérica `AppManager`, alias `self` e função `badCrypto`.
Impact: Leitura difícil e intenção obscura.
Recommendation: Nomes de domínio (`name`, `email`, `password`, `courseId`, `cardNumber`, `hashPassword`) (PB-15).

### F-14 [LOW] Console as Logging
Anti-pattern: AP-20
File: src/AppManager.js:45; src/utils.js:13; src/app.js:13
Description: `console.log` é usado para eventos da aplicação, e na linha 45 com dados sensíveis (ver F-02).
Impact: Sem níveis e sem controle de verbosidade.
Recommendation: Manter só o log de boot e logs sem dados sensíveis, centralizados num helper `logger` mínimo sobre `console` com nível (PB-15).

### F-15 [LOW] Dead Code / Unused Imports
Anti-pattern: AP-21
File: src/AppManager.js:2; src/utils.js:2-3, 5, 10
Description: `totalRevenue` é importado e nunca usado. `config.dbUser`, `config.dbPass` e `config.smtpUser` não têm nenhuma referência.
Impact: Ruído que sugere funcionalidades inexistentes.
Recommendation: Remover os imports e os campos não usados (PB-15).

### F-16 [LOW] Non-idiomatic Constructs
Anti-pattern: AP-22
File: src/AppManager.js:26, 29-33, 46, 52, 81, 90
Description: `const self = this` convive com arrow functions, há `let` em valores nunca reatribuídos e callbacks aninhados em vez de async/await.
Impact: Código mais verboso e propenso a erro de `this`.
Recommendation: `const`, async/await sobre wrappers promisificados do sqlite3, sem `self` (PB-15).

================================
Total: 16 findings
================================
