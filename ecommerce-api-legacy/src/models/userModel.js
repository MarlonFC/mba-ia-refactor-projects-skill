const crypto = require('crypto');

const SALT_BYTES = 16;
const KEY_LENGTH = 64;

// Hash com salt aleatório por usuário; formato armazenado: "salt:hash" (hex).
function hashPassword(plain) {
  const salt = crypto.randomBytes(SALT_BYTES).toString('hex');
  const hash = crypto.scryptSync(plain, salt, KEY_LENGTH).toString('hex');
  return `${salt}:${hash}`;
}

const createUserModel = (db) => ({
  findByEmail: (email) => db.get('SELECT id FROM users WHERE email = ?', [email]),

  // Sem senha informada, a conta fica sem senha utilizável (pass = NULL).
  async create({ name, email, password }) {
    const pass = password ? hashPassword(password) : null;
    const { lastID } = await db.run('INSERT INTO users (name, email, pass) VALUES (?, ?, ?)', [name, email, pass]);
    return lastID;
  },

  async deleteById(id) {
    const { changes } = await db.run('DELETE FROM users WHERE id = ?', [id]);
    return changes > 0;
  },
});

module.exports = { createUserModel, hashPassword };
