// Mensagem de sucesso mantida do contrato original.
const DELETE_USER_MESSAGE = 'Usuário deletado, mas as matrículas e pagamentos ficaram sujos no banco.';

const createUserController = (userService) => ({
  async deleteUser(req, res) {
    await userService.deleteUser(req.params.id);
    res.send(DELETE_USER_MESSAGE);
  },
});

module.exports = { createUserController };
