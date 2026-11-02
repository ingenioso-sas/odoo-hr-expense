# Copyright 2026
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl.html).

from odoo import SUPERUSER_ID, api


def post_init_hook(cr, registry):
    """Asigna por defecto la cuenta payable de la compañía a la regla de
    reembolso si está sin configurar.

    La línea contable del reembolso necesita una cuenta para poder generarse;
    en la confirmación de la nómina se ajusta automáticamente a la cuenta
    payable real de cada empleado.
    """
    with api.Environment.manage():
        env = api.Environment(cr, SUPERUSER_ID, {})
        rule = env.ref("hr_expense_payroll.rule_exp_reimb", raise_if_not_found=False)
        if rule and not rule.account_debit:
            default_payable = (
                env["account.account"]
                .search(
                    [
                        ("user_type_id.type", "=", "payable"),
                        ("deprecated", "=", False),
                        ("company_id", "=", env.company.id),
                    ],
                    limit=1,
                )
            )
            if default_payable:
                rule.account_debit = default_payable
