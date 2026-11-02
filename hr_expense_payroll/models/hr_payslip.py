# Copyright 2026
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl.html).

from odoo import _, fields, models
from odoo.tools.float_utils import float_is_zero

EXP_REIMB_CODE = "EXP_REIMB"


class HrPayslip(models.Model):
    _inherit = "hr.payslip"

    expense_sheet_ids = fields.Many2many(
        comodel_name="hr.expense.sheet",
        relation="hr_expense_sheet_payslip_rel",
        column1="payslip_id",
        column2="sheet_id",
        string="Expense Reports",
        copy=False,
        readonly=True,
        help="Expense reports reimbursed through this payslip.",
    )
    reversed_move_id = fields.Many2one(
        comodel_name="account.move",
        string="Reversed Move",
        copy=False,
        readonly=True,
        ondelete="set null",
        help="Payslip journal entry that was preserved and reversed on "
        "cancellation (audit trail).",
    )
    reversal_move_id = fields.Many2one(
        comodel_name="account.move",
        string="Reversal Move",
        copy=False,
        readonly=True,
        ondelete="set null",
        help="Reversal journal entry created when the payslip was cancelled.",
    )

    def _get_reimbursement_sheets(self, employee, date_from, date_to):
        """Reportes de gasto elegibles para reembolso vía nómina.

        Criterios: estado ``post`` (publicado y sin pagar), canal de pago
        ``payroll``, pagado por el empleado, saldo pendiente > 0 y con todos
        sus gastos devengados hasta el corte (``date_to``) de la nómina.
        Los reportes de periodos anteriores no pagados se arrastran.
        """
        sheets = self.env["hr.expense.sheet"].search(
            [
                ("state", "=", "post"),
                ("payment_channel", "=", "payroll"),
                ("payment_mode", "=", "own_account"),
                ("employee_id", "=", employee.id),
            ]
        )
        return sheets.filtered(
            lambda sheet: sheet.expense_line_ids
            and max(sheet.expense_line_ids.mapped("date")) <= date_to
            and sheet.amount_to_pay > 0.0
        )

    def get_inputs(self, contracts, date_from, date_to):
        """Inyecta (o ajusta) el input ``EXP_REIMB`` con el saldo pendiente
        de reembolso del empleado para el periodo de la nómina."""
        res = super().get_inputs(contracts, date_from, date_to)
        for contract in contracts:
            sheets = self._get_reimbursement_sheets(
                contract.employee_id, date_from, date_to
            )
            amount = sum(sheets.mapped("amount_to_pay"))
            handled = False
            for input_vals in res:
                if (
                    input_vals.get("code") == EXP_REIMB_CODE
                    and input_vals.get("contract_id") == contract.id
                ):
                    input_vals["amount"] = amount
                    handled = True
            if not handled and amount > 0.0:
                res.append(
                    {
                        "name": "Expense Reimbursement",
                        "code": EXP_REIMB_CODE,
                        "amount": amount,
                        "contract_id": contract.id,
                    }
                )
        # Se descartan los placeholders sin importe para no generar líneas
        # de nómina vacías
        return [
            input_vals
            for input_vals in res
            if not (
                input_vals.get("code") == EXP_REIMB_CODE
                and not input_vals.get("amount")
            )
        ]

    def compute_sheet(self):
        # Se refresca el input ANTES de calcular las líneas, ya que éstas se
        # generan dentro de super() a partir de los inputs almacenados
        self._refresh_reimbursement_inputs()
        return super().compute_sheet()

    def _refresh_reimbursement_inputs(self):
        """Refresca el importe del input ``EXP_REIMB`` y guarda en la nómina
        el snapshot de reportes que va a reembolsar (usado al confirmar)."""
        for payslip in self:
            inputs = payslip.input_line_ids.filtered(
                lambda input_line: input_line.code == EXP_REIMB_CODE
            )
            sheets = self.env["hr.expense.sheet"]
            amount = 0.0
            if (
                payslip.employee_id
                and payslip.date_from
                and payslip.date_to
                and not payslip.credit_note
            ):
                sheets = payslip._get_reimbursement_sheets(
                    payslip.employee_id, payslip.date_from, payslip.date_to
                )
                amount = sum(sheets.mapped("amount_to_pay"))
            if amount > 0.0:
                if inputs:
                    inputs[1:].unlink()
                    inputs[0].write({"amount": amount})
                else:
                    payslip.write(
                        {
                            "input_line_ids": [
                                (
                                    0,
                                    0,
                                    {
                                        "name": "Expense Reimbursement",
                                        "code": EXP_REIMB_CODE,
                                        "amount": amount,
                                        "contract_id": payslip.contract_id.id,
                                    },
                                )
                            ]
                        }
                    )
            else:
                inputs.unlink()
            # Se escribe ambos lados de la relación: además de poblar el
            # snapshot de la nómina, invalida la caché de `payslip_ids` del
            # reporte para que el hook de cancelación lo vea en la misma
            # transacción
            payslip.expense_sheet_ids = [(6, 0, sheets.ids)]
            for sheet in sheets:
                sheet.payslip_ids = [(4, payslip.id)]

    def action_payslip_done(self):
        res = super().action_payslip_done()
        for payslip in self:
            # Las notas crédito no reembolsan: el reverso de un reembolso se
            # hace cancelando la nómina (ver acción Cancel)
            if payslip.credit_note:
                continue
            payslip._fix_reimbursement_move_line()
            payslip._settle_expense_sheets()
        return res

    def _fix_reimbursement_move_line(self):
        """Ajusta la línea contable del reembolso a la cuenta payable y el
        partner comercial reales del empleado.

        La regla salarial tiene una única cuenta payable configurada; aquí se
        reescribe (sólo si difiere) a la cuenta del empleado para poder
        conciliarla con el asiento del gasto. El partner se corrige igual en
        ``hr.payslip.line._get_partner_id``.
        """
        self.ensure_one()
        move = self.move_id
        rule = self.env.ref(
            "hr_expense_payroll.rule_exp_reimb", raise_if_not_found=False
        )
        if not move or not rule:
            return
        employee = self.employee_id.sudo()
        address = employee.address_home_id
        if not address:
            return
        partner = address.commercial_partner_id
        address_company = address.with_context(force_company=self.company_id.id)
        payable_account = (
            address_company.property_account_payable_id
            or address_company.parent_id.property_account_payable_id
        )
        if not payable_account:
            return
        reimb_payslip_lines = self.line_ids.filtered(
            lambda payslip_line: payslip_line.code == EXP_REIMB_CODE
        )
        if not reimb_payslip_lines:
            return
        # Se identifica la línea contable por el nombre calculado en la propia
        # nómina (evita problemas de traducción) y por la cuenta de la regla
        line_name = reimb_payslip_lines[0].name
        lines = move.line_ids.filtered(
            lambda line: line.name == line_name
            and line.account_id == rule.account_debit
            and line.debit > 0.0
        )
        if not lines:
            return
        if all(
            line.account_id == payable_account and line.partner_id == partner
            for line in lines
        ):
            return
        if move.state == "posted":
            move.button_draft()
        lines.write({"account_id": payable_account.id, "partner_id": partner.id})
        move.post()

    def _settle_expense_sheets(self):
        """Concilia la línea payable de la nómina con la de cada reporte del
        snapshot y lo marca como pagado si el saldo queda a cero."""
        self.ensure_one()
        if not self.move_id or not self.expense_sheet_ids:
            return
        for sheet in self.expense_sheet_ids:
            if sheet.state != "post":
                continue
            account = sheet._get_employee_payable_account()
            if not account:
                continue
            sheet_lines = sheet.account_move_id.line_ids.filtered(
                lambda line: line.account_id == account and not line.reconciled
            )
            if not sheet_lines:
                continue
            payslip_lines = self.move_id.line_ids.filtered(
                lambda line: line.account_id == account
                and line.partner_id == sheet_lines[0].partner_id
                and not line.reconciled
            )
            if not payslip_lines:
                continue
            (sheet_lines + payslip_lines).reconcile()
            sheet.message_post(
                body=_("Reimbursed through payslip %s.") % self.display_name
            )
            rounding = sheet.currency_id.rounding
            if float_is_zero(sheet.amount_to_pay, precision_rounding=rounding):
                sheet.paid_expense_sheets()

    def action_payslip_cancel(self):
        """Cancela la nómina con reverso contable y libera los reportes.

        El módulo de contabilidad de nómina *borra* el asiento al cancelar;
        aquí se desvincula el asiento, se llama a ``super()`` y se genera un
        asiento de reverso en su lugar, conservando la auditoría.
        """
        # La validación del módulo de nómina (no cancelar 'done' directamente)
        # se respeta ANTES de efectuar cambios para no dejar estado parcial
        if any(payslip.state == "done" for payslip in self):
            return super().action_payslip_cancel()
        for payslip in self:
            if payslip.move_id:
                payslip._reopen_expense_sheets()
                payslip.reversed_move_id = payslip.move_id
                payslip.move_id = False
        res = super().action_payslip_cancel()
        for payslip in self:
            move = payslip.reversed_move_id
            if move.exists() and move.state == "posted":
                payslip.reversal_move_id = move._create_reversal_entry()
        return res

    def _reopen_expense_sheets(self):
        """Desconcilia los reportes del snapshot con el asiento de la nómina
        y los reabre (vuelven a estado ``post`` con saldo pendiente)."""
        self.ensure_one()
        if not self.move_id:
            return
        move_lines = self.move_id.line_ids
        for sheet in self.expense_sheet_ids:
            sheet_lines = sheet.account_move_id.line_ids
            common_full_reconciles = sheet_lines.mapped(
                "full_reconcile_id"
            ) & move_lines.mapped("full_reconcile_id")
            if common_full_reconciles:
                (sheet_lines + move_lines).filtered(
                    lambda line: line.full_reconcile_id in common_full_reconciles
                ).remove_move_reconcile()
            if sheet.state == "done":
                sheet.state = "post"
            sheet.payslip_ids = [(3, self.id)]
            sheet.message_post(
                body=_(
                    "Reimbursement released: payslip %s cancelled."
                )
                % self.display_name
            )
