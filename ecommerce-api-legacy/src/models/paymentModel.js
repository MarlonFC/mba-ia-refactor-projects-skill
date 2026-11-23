const PAYMENT_STATUS = Object.freeze({ PAID: 'PAID', DENIED: 'DENIED' });
const APPROVED_CARD_PREFIX = '4';

// Regra simulada do gateway: cartões iniciados em "4" são aprovados.
const authorize = (cardNumber) => (
  cardNumber.startsWith(APPROVED_CARD_PREFIX) ? PAYMENT_STATUS.PAID : PAYMENT_STATUS.DENIED
);

const createPaymentModel = (db) => ({
  authorize,
  async create({ enrollmentId, amount, status }) {
    const { lastID } = await db.run(
      'INSERT INTO payments (enrollment_id, amount, status) VALUES (?, ?, ?)',
      [enrollmentId, amount, status],
    );
    return lastID;
  },
});

module.exports = createPaymentModel;
module.exports.PAYMENT_STATUS = PAYMENT_STATUS;
