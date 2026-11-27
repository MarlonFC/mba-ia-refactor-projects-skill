const { AppError } = require('../middlewares/errorHandler');

// Contrato de entrada original: usr, eml, pwd, c_id, card.
function parseCheckoutBody(body = {}) {
  const { usr: name, eml: email, pwd: password, c_id: courseId, card: cardNumber } = body;
  if (!name || !email || !courseId || !cardNumber) throw new AppError(400, 'Bad Request');
  if (typeof cardNumber !== 'string') throw new AppError(400, 'Bad Request');
  return { name, email, password, courseId, cardNumber };
}

const createCheckoutController = (checkoutService) => ({
  async checkout(req, res) {
    const { enrollmentId } = await checkoutService.checkout(parseCheckoutBody(req.body));
    res.status(200).json({ msg: 'Sucesso', enrollment_id: enrollmentId });
  },
});

module.exports = { createCheckoutController };
