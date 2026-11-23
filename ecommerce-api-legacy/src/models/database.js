const sqlite3 = require('sqlite3');

const SCHEMA = `
  CREATE TABLE users (id INTEGER PRIMARY KEY, name TEXT, email TEXT, pass TEXT);
  CREATE TABLE courses (id INTEGER PRIMARY KEY, title TEXT, price REAL, active INTEGER);
  CREATE TABLE enrollments (id INTEGER PRIMARY KEY, user_id INTEGER, course_id INTEGER);
  CREATE TABLE payments (id INTEGER PRIMARY KEY, enrollment_id INTEGER, amount REAL, status TEXT);
  CREATE TABLE audit_logs (id INTEGER PRIMARY KEY, action TEXT, created_at DATETIME);
`;

// Conexão SQLite com API em Promises e transações serializadas.
function openDatabase(filename) {
  const raw = new sqlite3.Database(filename);

  const db = {
    run: (sql, params = []) => new Promise((resolve, reject) => {
      raw.run(sql, params, function onRun(err) {
        if (err) return reject(err);
        return resolve({ lastID: this.lastID, changes: this.changes });
      });
    }),
    get: (sql, params = []) => new Promise((resolve, reject) => {
      raw.get(sql, params, (err, row) => (err ? reject(err) : resolve(row)));
    }),
    all: (sql, params = []) => new Promise((resolve, reject) => {
      raw.all(sql, params, (err, rows) => (err ? reject(err) : resolve(rows)));
    }),
    exec: (sql) => new Promise((resolve, reject) => {
      raw.exec(sql, (err) => (err ? reject(err) : resolve()));
    }),
  };

  // A conexão é única: transações entram em fila para que requisições
  // concorrentes não intercalem comandos dentro do mesmo BEGIN.
  let queue = Promise.resolve();
  db.transaction = (work) => {
    const result = queue.then(async () => {
      await db.run('BEGIN');
      try {
        const value = await work();
        await db.run('COMMIT');
        return value;
      } catch (err) {
        await db.run('ROLLBACK');
        throw err;
      }
    });
    queue = result.catch(() => {});
    return result;
  };

  return db;
}

async function initDatabase(db, { userModel }) {
  await db.exec(SCHEMA);
  await userModel.create({ name: 'Leonan', email: 'leonan@fullcycle.com.br', password: '123' });
  await db.run("INSERT INTO courses (title, price, active) VALUES ('Clean Architecture', 997.00, 1), ('Docker', 497.00, 1)");
  await db.run('INSERT INTO enrollments (user_id, course_id) VALUES (1, 1)');
  await db.run("INSERT INTO payments (enrollment_id, amount, status) VALUES (1, 997.00, 'PAID')");
}

module.exports = { openDatabase, initDatabase };
