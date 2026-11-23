const crypto = require('crypto');
const { promisify } = require('util');

const scrypt = promisify(crypto.scrypt);
const SALT_BYTES = 16;
const KEY_LENGTH = 64;

async function hashPassword(plain) {
  const salt = crypto.randomBytes(SALT_BYTES).toString('hex');
  const hash = await scrypt(plain, salt, KEY_LENGTH);
  return `scrypt$${salt}$${hash.toString('hex')}`;
}

module.exports = (db) => ({
  findByEmail: (email) => db.get('SELECT id FROM users WHERE email = ?', [email]),

  // Sem senha informada não há credencial: grava NULL em vez de uma senha padrão.
  async create({ name, email, password }) {
    const passwordHash = password ? await hashPassword(password) : null;
    const { lastID } = await db.run(
      'INSERT INTO users (name, email, pass) VALUES (?, ?, ?)',
      [name, email, passwordHash],
    );
    return lastID;
  },

  // Remove apenas o usuário. Matrículas e pagamentos são histórico financeiro e
  // permanecem (o relatório os exibe como aluno "Unknown").
  async delete(userId) {
    const { changes } = await db.run('DELETE FROM users WHERE id = ?', [userId]);
    return changes > 0;
  },
});
