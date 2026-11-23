const { AppError } = require('../middlewares/errorHandler');
const { PAYMENT_STATUS } = require('../models/paymentModel');

const isNonEmptyString = (value) => typeof value === 'string' && value.length > 0;

// Contrato de entrada original: usr, eml, pwd, c_id, card.
function parseCheckoutInput(body) {
  const { usr, eml, pwd, c_id: courseId, card } = body || {};
  const valid = isNonEmptyString(usr)
    && isNonEmptyString(eml)
    && isNonEmptyString(card)
    && Boolean(courseId)
    && (pwd === undefined || pwd === null || typeof pwd === 'string');
  if (!valid) throw new AppError(400, 'Bad Request');
  return { name: usr, email: eml, password: pwd, courseId, cardNumber: card };
}

module.exports = ({ transaction, courseModel, userModel, enrollmentModel, paymentModel, auditLogModel }) => ({
  async checkout(body) {
    const { name, email, password, courseId, cardNumber } = parseCheckoutInput(body);

    const course = await courseModel.findActiveById(courseId);
    if (!course) throw new AppError(404, 'Curso não encontrado');

    const status = paymentModel.authorize(cardNumber);
    if (status === PAYMENT_STATUS.DENIED) throw new AppError(400, 'Pagamento recusado');

    return transaction(async () => {
      const existing = await userModel.findByEmail(email);
      const userId = existing ? existing.id : await userModel.create({ name, email, password });
      const enrollmentId = await enrollmentModel.create({ userId, courseId });
      await paymentModel.create({ enrollmentId, amount: course.price, status });
      await auditLogModel.record(`Checkout curso ${courseId} por ${userId}`);
      return { enrollmentId };
    });
  },
});
