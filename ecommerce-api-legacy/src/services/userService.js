const createUserService = ({ db, userModel, auditLogModel }) => ({
  // Matrículas e pagamentos são histórico financeiro: preservados (o relatório
  // passa a exibir o aluno como "Unknown"); a exclusão fica auditada.
  deleteUser(id) {
    return db.transaction(async () => {
      const deleted = await userModel.deleteById(id);
      if (deleted) await auditLogModel.record(`Usuário ${id} removido`);
      return deleted;
    });
  },
});

module.exports = { createUserService };
