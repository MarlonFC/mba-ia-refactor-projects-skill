const { AppError } = require('../middlewares/errorHandler');
const { authorize, maskCard, PAYMENT_STATUS } = require('../models/paymentModel');

const createCheckoutService = ({ db, courseModel, userModel, enrollmentModel, paymentModel, auditLogModel }) => ({
  async checkout({ name, email, password, courseId, cardNumber }) {
    const course = await courseModel.findActiveById(courseId);
    if (!course) throw new AppError(404, 'Curso não encontrado');

    console.log(`Processando pagamento do cartão ${maskCard(cardNumber)}`);
    const status = authorize(cardNumber);
    if (status === PAYMENT_STATUS.DENIED) throw new AppError(400, 'Pagamento recusado');

    // Usuário, matrícula, pagamento e auditoria: tudo ou nada.
    return db.transaction(async () => {
      const existing = await userModel.findByEmail(email);
      const userId = existing ? existing.id : await userModel.create({ name, email, password });
      const enrollmentId = await enrollmentModel.create(userId, courseId);
      await paymentModel.create(enrollmentId, course.price, status);
      await auditLogModel.record(`Checkout curso ${courseId} por ${userId}`);
      return { enrollmentId };
    });
  },
});

module.exports = { createCheckoutService };
