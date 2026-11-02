# Copyright 2026
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl.html).

from odoo import models


class HrPayrollStructure(models.Model):
    _inherit = "hr.payroll.structure"

    def get_all_rules(self):
        """Asegura que la regla de reembolso ``EXP_REIMB`` esté siempre
        disponible, en cualquier estructura salarial.

        Así el puente funciona sin parchear cada estructura (incluida la
        localización colombiana). La condición python de la regla garantiza
        que sólo se aplique cuando existe el input con importe > 0.
        """
        rules = super().get_all_rules()
        rule = self.env.ref(
            "hr_expense_payroll.rule_exp_reimb", raise_if_not_found=False
        )
        if rule and rule.active and rule.id not in [rule_id for rule_id, _s in rules]:
            rules.append((rule.id, rule.sequence))
        return rules
