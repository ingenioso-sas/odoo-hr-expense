# Copyright 2019 Tecnativa - Ernesto Tejeda
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl.html).

from odoo import _, fields, models


class HrExpenseSheet(models.Model):
    _inherit = "hr.expense.sheet"

    # Asiento original que fue revertido (traza de auditoría)
    reversed_move_id = fields.Many2one(
        comodel_name="account.move",
        string="Reversed Move",
        copy=False,
        readonly=True,
        ondelete="set null",
        help="Original expense journal entry that was reversed.",
    )
    # Asiento de reverso generado por esta cancelación
    reversal_move_id = fields.Many2one(
        comodel_name="account.move",
        string="Reversal Move",
        copy=False,
        readonly=True,
        ondelete="set null",
        help="Journal entry created to reverse the original expense entry.",
    )

    def _check_cancel_allowed(self):
        """Hook de validación previa a la cancelación/reverso.

        Permite que otros módulos (p. ej. el puente con nómina) bloqueen la
        cancelación cuando existan vínculos que deban liberarse primero.
        """
        return True

    def action_cancel(self):
        """Cancela el reporte generando reversos contables.

        Cambio de comportamiento respecto a la versión original del módulo:
        ya **no** se borran (`unlink`) asientos ni pagos; se conservan los
        registros para auditoría y se generan asientos de reverso /
        cancelaciones de pago en su lugar.
        """
        for sheet in self:
            sheet._check_cancel_allowed()
            account_move = sheet.account_move_id
            payments = self.env["account.payment"].search(
                [("expense_sheet_id", "=", sheet.id), ("state", "!=", "cancelled")]
            )
            # Caso: cancelar la factura de proveedor creada por hr_expense_invoice
            if account_move:
                sheet._remove_reconcile_hr_invoice(account_move)
            if sheet.state == "done":
                if sheet.expense_line_ids[:1].payment_mode == "own_account":
                    # Se desconcilian y cancelan los pagos directos al empleado,
                    # conservando sus asientos (estado 'cancel', sin borrar)
                    sheet._remove_move_reconcile(payments, account_move)
                    sheet._cancel_payments(payments)
                else:
                    # En modo 'company_account' el pago comparte asiento con el
                    # gasto: sólo se marca el pago como cancelado; el asiento se
                    # revierte más abajo junto al resto del reporte
                    sheet._cancel_payments(payments)
            # Reverso contable del asiento de gasto (se conserva el original)
            if account_move.exists():
                sheet._reverse_expense_move(account_move)
                sheet.write(
                    {
                        "reversed_move_id": account_move.id,
                        "account_move_id": False,
                    }
                )
            sheet.state = "approve"
            sheet.message_post(
                body=_(
                    "Expense report cancelled: the original journal entry was "
                    "reversed instead of deleted."
                )
            )

    def action_sheet_move_create(self):
        res = super().action_sheet_move_create()
        if self.expense_line_ids[0].payment_mode == "company_account":
            self.account_move_id.mapped("line_ids.payment_id").write(
                {"expense_sheet_id": self.id}
            )
        return res

    def _reverse_expense_move(self, account_move):
        """Revierte el asiento de gasto conservando el original publicado.

        Delega en ``account.move._create_reversal_entry`` (reutilizable por
        otros módulos, p. ej. el puente con nómina).
        """
        self.ensure_one()
        reversal = account_move._create_reversal_entry()
        self.reversal_move_id = reversal
        return reversal

    def _remove_reconcile_hr_invoice(self, account_move):
        """Cancela la factura creada automáticamente por hr_expense_invoice.

        Se mantiene el comportamiento estándar de Odoo: la factura se pone en
        estado 'cancel' (no se borra).
        """
        reconcile = account_move.mapped("line_ids.full_reconcile_id")
        aml = self.env["account.move.line"].search(
            [("full_reconcile_id", "in", reconcile.ids)]
        )
        exp_move_line = aml.filtered(lambda l: l.move_id.id != account_move.id)
        # set state to cancel
        for move in exp_move_line.move_id:
            if move.state == "posted":
                move.button_draft()
                move.button_cancel()

    def _remove_move_reconcile(self, payments, account_move):
        """Elimina sólo las conciliaciones hechas con los pagos generados
        automáticamente por el módulo hr_expense (los registros se conservan).
        """
        payments_aml = payments.mapped("move_line_ids")
        aml_unreconcile = payments_aml.filtered(lambda l: l.reconciled)
        aml_unreconcile.remove_move_reconcile()

    def _cancel_payments(self, payments):
        """Cancela los pagos sin borrarlos.

        Los asientos de los pagos directos ('own_account') se cancelan con
        `button_cancel` (conservando su numeración); los pagos ligados al
        asiento del gasto ('company_account') sólo cambian de estado, ya que
        su asiento es el del propio gasto y se revierte por separado.
        """
        sheet_moves = self.mapped("account_move_id")
        for payment in payments:
            for move in payment.move_line_ids.mapped("move_id"):
                if move in sheet_moves:
                    continue
                if move.state == "posted":
                    move.button_cancel()
            payment.cancel()
