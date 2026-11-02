# Copyright 2026
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl.html).

{
    "name": "HR Expense Payroll Bridge - Colombia",
    "version": "13.0.1.0.0",
    "category": "Human Resources",
    "license": "AGPL-3",
    "author": "Custom Addons",
    "website": "https://github.com/OCA/hr-expense",
    "summary": "Includes expense reimbursements in the Colombian payslip "
    "NET (Neto a Pagar) without touching social security bases",
    "depends": [
        "hr_expense_payroll",
        "l10n_co_hr_payroll_community",
    ],
    "data": ["data/hr_payroll_data_co.xml"],
    "installable": True,
}
