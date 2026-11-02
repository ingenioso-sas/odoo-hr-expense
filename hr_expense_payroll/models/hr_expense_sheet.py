# Copyright 2026
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl.html).

from odoo import _, api, fields, models
from odoo.exceptions import UserError, ValidationError
from odoo.tools.float_utils import float_compare


class HrExpenseSheet(models.Model):
    _inherit = "hr.expense.sheet"

    payment_channel = fields.Selection(
        selection=[
            ("direct", "Direct Payment"),
            ("payroll", "Payroll"),
        ],
        string="Payment Channel",
        default="direct",
        copy=False,
        help="How the reimbursement is paid: directly from a bank/cash "
        "journal (Register Payment) or through the employee payroll.",
    )
    payslip_ids = fields.Many2many(
        comodel_name="hr.payslip",
        relation="hr_expense_sheet_payslip_rel",
        column1="sheet_id",
        column2="payslip_id",
        string="Payslips",
        copy=False,
        readonly=True,
        help="Payslips that reimbursed (part of) this expense report.",
    )
    amount_to_pay = fields.Monetary(
        string="Amount To Pay",
        compute="_compute_amount_to_pay",
        help="Pending amount to reimburse the employee (company currency). "
        "It decreases as direct payments or payroll reimbursements are "
        "reconciled against the expense report.",
    )

    @api.depends(
        "total_amount",
        "payment_mode",
        "currency_id",
        "account_move_id",
        "account_move_id.line_ids.amount_residual",
        "payslip_ids",
    )
    def _compute_amount_to_pay(self):
        for sheet in self:
            sheet.amount_to_pay = sheet._get_amount_to_pay()

    def _get_employee_payable_account(self):
        """Devuelve la cuenta payable real del empleado.

        Es la misma que usa el módulo ``hr_expense`` para acreditar la deuda
        con el empleado, garantizando que la conciliación con la nómina sea
        posible.
        """
        self.ensure_one()
        employee = self.employee_id.sudo()
        address = employee.address_home_id
        if not address:
            return self.env["account.account"]
        address = address.with_context(force_company=self.company_id.id)
        return (
            address.property_account_payable_id
            or address.parent_id.property_account_payable_id
        )

    def _get_amount_to_pay(self):
        """Saldo por pagar al empleado en moneda de la compañía.

        Se calcula desde el residual de las líneas payable del asiento del
        gasto (cuenta real del empleado), lo que excluye correctamente las
        líneas de anticipo de ``hr_expense_advance_clearing`` y refleja tanto
        los pagos directos como los reembolsos conciliados vía nómina.
        """
        self.ensure_one()
        if self.payment_mode != "own_account":
            return 0.0
        if not self.account_move_id:
            # Aún sin publicar: se adeuda el total del reporte
            return self.total_amount
        account = self._get_employee_payable_account()
        if not account:
            return 0.0
        # amount_residual se expresa con signo (crédito = negativo); el saldo
        # por pagar al empleado es el valor absoluto del residual
        residual = abs(
            sum(
                self.account_move_id.line_ids.filtered(
                    lambda line: line.account_id == account
                ).mapped("amount_residual")
            )
        )
        return residual

    @api.constrains("payment_channel")
    def _check_payment_channel(self):
        for sheet in self:
            if (
                sheet.payment_channel == "payroll"
                and sheet.payment_mode != "own_account"
            ):
                raise ValidationError(
                    _(
                        "The payroll payment channel is only available for "
                        "expenses paid by the employee (to reimburse)."
                    )
                )

    def write(self, vals):
        if "payment_channel" in vals:
            for sheet in self:
                rounding = sheet.currency_id.rounding
                already_paid = sheet.state == "done" or (
                    sheet.state == "post"
                    and float_compare(
                        sheet.amount_to_pay,
                        sheet.total_amount,
                        precision_rounding=rounding,
                    )
                    < 0
                )
                if already_paid and vals["payment_channel"] != sheet.payment_channel:
                    raise UserError(
                        _(
                            "You cannot change the payment channel of a "
                            "reimbursed expense report (%s)."
                        )
                        % sheet.name
                    )
        return super().write(vals)

    def action_cancel(self):
        """Bloquea el reverso si el reporte fue (parcialmente) reembolsado
        a través de nómina: hay que cancelar primero la nómina para liberar
        la conciliación.

        Se sobrescribe ``action_cancel`` (además del hook
        ``_check_cancel_allowed``) para garantizar la validación en cualquier
        orden de carga de módulos.
        """
        for sheet in self:
            active_payslips = sheet.payslip_ids.filtered(
                lambda payslip: payslip.state != "cancel"
            )
            if active_payslips:
                raise UserError(
                    _(
                        "Expense report %s was reimbursed through payroll "
                        "(payslip(s): %s). Cancel the payslip(s) first to "
                        "release the reimbursement."
                    )
                    % (sheet.name, ", ".join(active_payslips.mapped("name")))
                )
        return super().action_cancel()

    def _check_cancel_allowed(self):
        """Hook de validación previa (versión puente): reutiliza la misma
        comprobación que ``action_cancel``."""
        res = super()._check_cancel_allowed()
        for sheet in self:
            active_payslips = sheet.payslip_ids.filtered(
                lambda payslip: payslip.state != "cancel"
            )
            if active_payslips:
                raise UserError(
                    _(
                        "Expense report %s was reimbursed through payroll "
                        "(payslip(s): %s). Cancel the payslip(s) first to "
                        "release the reimbursement."
                    )
                    % (sheet.name, ", ".join(active_payslips.mapped("name")))
                )
        return res


class HrExpense(models.Model):
    _inherit = "hr.expense"

    def write(self, vals):
        """Revalida el canal de pago del reporte si cambia `payment_mode`.

        `payment_mode` en el reporte es un related no escribible, por lo que
        `@api.constrains` no puede vigilarlo directamente.
        """
        res = super().write(vals)
        if "payment_mode" in vals:
            self.mapped("sheet_id")._check_payment_channel()
        return res
