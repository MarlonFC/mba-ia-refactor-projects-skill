const { PAYMENT_STATUS } = require('../models/paymentModel');

const createReportService = ({ courseModel }) => ({
  // Receita e alunos por curso, a partir de uma única consulta.
  async financialReport() {
    const rows = await courseModel.listEnrollmentPayments();
    const byCourse = new Map();

    rows.forEach((row) => {
      if (!byCourse.has(row.course_id)) {
        byCourse.set(row.course_id, { course: row.course_title, revenue: 0, students: [] });
      }
      if (row.enrollment_id === null) return;

      const entry = byCourse.get(row.course_id);
      if (row.payment_status === PAYMENT_STATUS.PAID) entry.revenue += row.payment_amount;
      entry.students.push({
        student: row.student_name ?? 'Unknown',
        paid: row.payment_amount ?? 0,
      });
    });

    return [...byCourse.values()];
  },
});

module.exports = { createReportService };
