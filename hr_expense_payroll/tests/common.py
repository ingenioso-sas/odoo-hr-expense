# Copyright 2026
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl.html).

from datetime import timedelta

from dateutil.relativedelta import relativedelta

from odoo import fields
from odoo.tests.common import TransactionCase


class TestExpensePayrollCommon(TransactionCase):
    def setUp(self):
        super().setUp()
        company = self.env.ref("base.main_company")
        account_type_payable = self.env.ref("account.data_account_type_payable")
        account_type_liquidity = self.env.ref("account.data_account_type_liquidity")
        account_type_expense = self.env.ref("account.data_account_type_expenses")

        self.payable_account = self.env["account.account"].create(
            {
                "name": "Employee Payable Test",
                "code": "999901",
                "user_type_id": account_type_payable.id,
                "reconcile": True,
            }
        )
        self.other_payable_account = self.env["account.account"].create(
            {
                "name": "Other Payable Test",
                "code": "999902",
                "user_type_id": account_type_payable.id,
                "reconcile": True,
            }
        )
        self.expense_account = self.env["account.account"].create(
            {
                "name": "Expense Account Test",
                "code": "660001",
                "user_type_id": account_type_expense.id,
            }
        )
        self.bank_account = self.env["account.account"].create(
            {
                "name": "Bank Account Test",
                "code": "110001",
                "user_type_id": account_type_liquidity.id,
            }
        )
        self.payment_journal = self.env["account.journal"].create(
            {
                "name": "Bank Journal Test",
                "code": "BNKT",
                "type": "bank",
                "company_id": company.id,
                "default_credit_account_id": self.bank_account.id,
                "default_debit_account_id": self.bank_account.id,
            }
        )
        self.expense_journal = self.env["account.journal"].create(
            {
                "name": "Expense Journal Test",
                "code": "EXPT",
                "type": "purchase",
                "company_id": company.id,
            }
        )
        self.salary_journal = self.env["account.journal"].create(
            {
                "name": "Salary Journal Test",
                "code": "SALT",
                "type": "general",
                "company_id": company.id,
                "default_credit_account_id": self.bank_account.id,
                "default_debit_account_id": self.bank_account.id,
            }
        )
        self.home_partner = self.env["res.partner"].create(
            {
                "name": "Employee Home Test",
                "property_account_payable_id": self.payable_account.id,
            }
        )
        self.employee = self.env["hr.employee"].create(
            {
                "name": "Test Employee",
                "address_home_id": self.home_partner.id,
            }
        )
        structure = self.env["hr.payroll.structure"].create(
            {
                "name": "Test Structure",
                "code": "TST",
                "company_id": company.id,
            }
        )
        self.contract = self.env["hr.contract"].create(
            {
                "name": "Test Contract",
                "employee_id": self.employee.id,
                "wage": 1000.0,
                "type_id": self.env.ref(
                    "hr_contract_types.hr_contract_type_emp"
                ).id,
                "resource_calendar_id": self.env.ref(
                    "resource.resource_calendar_std"
                ).id,
                "struct_id": structure.id,
            }
        )
        self.product = self.env["product.product"].create(
            {
                "name": "Test Expense Product",
                "type": "service",
                "property_account_expense_id": self.expense_account.id,
            }
        )
        self.rule = self.env.ref("hr_expense_payroll.rule_exp_reimb")
        # Cuenta payable configurada por defecto en la regla
        self.rule.account_debit = self.payable_account
        today = fields.Date.today()
        self.period_from = today.replace(day=1)
        self.period_to = self.period_from + relativedelta(months=1) - timedelta(
            days=1
        )

    def _create_sheet(self, channel="payroll", amount=100.0, date=None):
        date = date or fields.Date.today()
        sheet = self.env["hr.expense.sheet"].create(
            {
                "employee_id": self.employee.id,
                "name": "Test Expense Sheet",
                "journal_id": self.expense_journal.id,
            }
        )
        self.env["hr.expense"].create(
            {
                "name": "Test Expense",
                "employee_id": self.employee.id,
                "product_id": self.product.id,
                "unit_amount": amount,
                "quantity": 1.0,
                "date": date,
                "sheet_id": sheet.id,
                "payment_mode": "own_account",
            }
        )
        sheet.payment_channel = channel
        sheet.action_submit_sheet()
        sheet.approve_expense_sheets()
        sheet.action_sheet_move_create()
        return sheet

    def _create_payslip(self, date_from=None, date_to=None, credit_note=False):
        return self.env["hr.payslip"].create(
            {
                "name": "Test Payslip",
                "employee_id": self.employee.id,
                "contract_id": self.contract.id,
                "date_from": date_from or self.period_from,
                "date_to": date_to or self.period_to,
                "journal_id": self.salary_journal.id,
                "credit_note": credit_note,
            }
        )
