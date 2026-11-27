const express = require('express');
const config = require('./config');
const { openDatabase, initDatabase } = require('./models/database');
const { createUserModel } = require('./models/userModel');
const { createCourseModel } = require('./models/courseModel');
const { createEnrollmentModel } = require('./models/enrollmentModel');
const { createPaymentModel } = require('./models/paymentModel');
const { createAuditLogModel } = require('./models/auditLogModel');
const { createCheckoutService } = require('./services/checkoutService');
const { createReportService } = require('./services/reportService');
const { createUserService } = require('./services/userService');
const { createCheckoutController } = require('./controllers/checkoutController');
const { createReportController } = require('./controllers/reportController');
const { createUserController } = require('./controllers/userController');
const checkoutRoutes = require('./routes/checkoutRoutes');
const adminRoutes = require('./routes/adminRoutes');
const userRoutes = require('./routes/userRoutes');
const { createRequireAdmin } = require('./middlewares/auth');
const { errorHandler } = require('./middlewares/errorHandler');

// Composition root: cria a conexão e injeta as dependências em cada camada.
async function main() {
  const db = openDatabase(config.dbPath);
  await initDatabase(db);

  const models = {
    db,
    userModel: createUserModel(db),
    courseModel: createCourseModel(db),
    enrollmentModel: createEnrollmentModel(db),
    paymentModel: createPaymentModel(db),
    auditLogModel: createAuditLogModel(db),
  };
  const requireAdmin = createRequireAdmin(config.adminToken);

  const app = express();
  app.use(express.json());
  app.use(checkoutRoutes(createCheckoutController(createCheckoutService(models))));
  app.use(adminRoutes(createReportController(createReportService(models)), requireAdmin));
  app.use(userRoutes(createUserController(createUserService(models)), requireAdmin));
  app.use(errorHandler);

  app.listen(config.port, () => {
    console.log(`Frankenstein LMS rodando na porta ${config.port}...`);
  });
}

main().catch((err) => {
  console.error(err);
  process.exit(1);
});
