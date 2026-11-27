const PAYMENT_STATUS = Object.freeze({ PAID: 'PAID', DENIED: 'DENIED' });
const APPROVED_CARD_PREFIX = '4';

// Gateway simulado: cartões que começam com o prefixo aprovado são pagos.
const authorize = (cardNumber) => (
  cardNumber.startsWith(APPROVED_CARD_PREFIX) ? PAYMENT_STATUS.PAID : PAYMENT_STATUS.DENIED
);

const maskCard = (cardNumber) => `****${cardNumber.slice(-4)}`;

const createPaymentModel = (db) => ({
  create: (enrollmentId, amount, status) => db.run(
    'INSERT INTO payments (enrollment_id, amount, status) VALUES (?, ?, ?)', [enrollmentId, amount, status],
  ),
});

module.exports = { createPaymentModel, authorize, maskCard, PAYMENT_STATUS };
