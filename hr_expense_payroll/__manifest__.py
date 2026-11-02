# Copyright 2026
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl.html).

{
    "name": "HR Expense Payroll Bridge",
    "version": "13.0.1.0.0",
    "category": "Human Resources",
    "license": "AGPL-3",
    "author": "Custom Addons",
    "website": "https://github.com/OCA/hr-expense",
    "summary": "Reimburse employee expenses through payroll with proper "
    "accounting reconciliation",
    "depends": [
        "hr_expense",
        "hr_expense_payment_difference",
        "hr_expense_cancel",
        "hr_payroll_community",
        "hr_payroll_account_community",
    ],
    "data": [
        "data/hr_payroll_data.xml",
        "views/hr_expense_sheet_views.xml",
        "views/hr_payslip_views.xml",
    ],
    "post_init_hook": "post_init_hook",
    "installable": True,
}
