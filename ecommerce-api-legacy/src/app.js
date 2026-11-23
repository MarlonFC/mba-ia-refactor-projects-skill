const express = require('express');
const config = require('./config');
const { openDatabase, initDatabase } = require('./models/database');
const createUserModel = require('./models/userModel');
const createCourseModel = require('./models/courseModel');
const createEnrollmentModel = require('./models/enrollmentModel');
const createPaymentModel = require('./models/paymentModel');
const createAuditLogModel = require('./models/auditLogModel');
const createCheckoutController = require('./controllers/checkoutController');
const createReportController = require('./controllers/reportController');
const createUserController = require('./controllers/userController');
const checkoutRoutes = require('./views/checkoutRoutes');
const adminRoutes = require('./views/adminRoutes');
const userRoutes = require('./views/userRoutes');
const { errorHandler } = require('./middlewares/errorHandler');

// Banco em memória: schema e seed são recriados a cada boot.
const DATABASE_FILE = ':memory:';

async function start() {
  const db = openDatabase(DATABASE_FILE);
  const userModel = createUserModel(db);
  const courseModel = createCourseModel(db);
  await initDatabase(db, { userModel });

  const checkoutController = createCheckoutController({
    transaction: db.transaction,
    courseModel,
    userModel,
    enrollmentModel: createEnrollmentModel(db),
    paymentModel: createPaymentModel(db),
    auditLogModel: createAuditLogModel(db),
  });

  const app = express();
  app.use(express.json());
  app.use(checkoutRoutes(checkoutController));
  app.use(adminRoutes(createReportController({ courseModel })));
  app.use(userRoutes(createUserController({ userModel })));
  app.use(errorHandler);

  app.listen(config.port, () => {
    console.info(`LMS API rodando na porta ${config.port}`);
  });
}

start().catch((err) => {
  console.error('Falha ao iniciar a aplicação', err);
  process.exit(1);
});
