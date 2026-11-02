# Copyright 2026
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl.html).

from odoo import models


class HrPayslipLine(models.Model):
    _inherit = "hr.payslip.line"

    def _get_partner_id(self, credit_account):
        """Usa el partner comercial del domicilio del empleado para las
        líneas payable/receivable.

        El asiento del gasto usa ``address_home_id.commercial_partner_id``;
        sin esta corrección la conciliación gasto↔nómina fallaría cuando el
        domicilio del empleado es un contacto hijo.
        """
        res = super()._get_partner_id(credit_account)
        address = self.slip_id.employee_id.address_home_id
        if res and address and res == address.id:
            commercial = address.commercial_partner_id
            if commercial.id != res:
                return commercial.id
        return res
