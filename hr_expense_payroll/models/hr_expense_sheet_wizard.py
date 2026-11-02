# Copyright 2026
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl.html).

from odoo import _, api, models
from odoo.exceptions import UserError
from odoo.tools.float_utils import float_compare


class HrExpenseSheetRegisterPaymentWizard(models.TransientModel):
    _inherit = "hr.expense.sheet.register.payment.wizard"

    @api.model
    def default_get(self, fields_list):
        res = super().default_get(fields_list)
        active_id = self._context.get("active_id")
        if (
            self._context.get("active_model") == "hr.expense.sheet"
            and active_id
        ):
            sheet = self.env["hr.expense.sheet"].browse(active_id)
            if sheet.payment_channel == "payroll":
                raise UserError(
                    _(
                        "This expense report is configured to be paid "
                        "through payroll. Change its payment channel if you "
                        "want to pay it directly."
                    )
                )
            if "amount" in fields_list:
                # Saldo real por pagar (no el total del reporte)
                res["amount"] = sheet.amount_to_pay
        return res

    def expense_post_payment(self):
        for wizard in self:
            sheet = wizard.expense_sheet_id
            if sheet.payment_channel == "payroll":
                raise UserError(
                    _(
                        "This expense report is configured to be paid "
                        "through payroll. Change its payment channel if you "
                        "want to pay it directly."
                    )
                )
            rounding = sheet.currency_id.rounding
            if (
                float_compare(
                    wizard.amount, sheet.amount_to_pay, precision_rounding=rounding
                )
                > 0
            ):
                raise UserError(
                    _(
                        "You cannot pay more (%s) than the pending amount "
                        "of the expense report."
                    )
                    % wizard.amount
                )
        return super().expense_post_payment()
