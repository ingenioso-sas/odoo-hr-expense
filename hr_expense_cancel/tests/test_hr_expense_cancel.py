# Copyright 2019 Tecnativa - Ernesto Tejeda
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

import odoo.tests.common as common

from ..hooks import post_init_hook


class TestHrExpenseCancel(common.TransactionCase):
    def setUp(self):
        super(TestHrExpenseCancel, self).setUp()
        company = self.env.ref("base.main_company")
        account_type_payable = self.env.ref("account.data_account_type_payable")
        account_type_expense = self.env.ref("account.data_account_type_expenses")
        account_type_liquidity = self.env.ref("account.data_account_type_liquidity")

        # Datos propios: los tests no dependen de datos demo
        self.payable_account = self.env["account.account"].create(
            {
                "name": "Employee Payable Test",
                "code": "999801",
                "user_type_id": account_type_payable.id,
                "reconcile": True,
            }
        )
        self.expense_account = self.env["account.account"].create(
            {
                "name": "Expense Account Test",
                "code": "669801",
                "user_type_id": account_type_expense.id,
            }
        )
        self.bank_account = self.env["account.account"].create(
            {
                "name": "Bank Account Test",
                "code": "119801",
                "user_type_id": account_type_liquidity.id,
            }
        )
        self.home_partner = self.env["res.partner"].create(
            {
                "name": "Employee Home Test",
                "property_account_payable_id": self.payable_account.id,
            }
        )
        self.employee = self.env.ref("hr.employee_admin")
        self.employee.address_home_id = self.home_partner

        self.partner = self.env["res.partner"].create(
            {
                "name": "Test partner",
                # Misma cuenta payable que el empleado: el pago se concilia
                # con el asiento del gasto (misma cuenta requerida)
                "property_account_payable_id": self.payable_account.id,
            }
        )
        self.payment_obj = self.env["account.payment"]
        # Diario de pago de la MISMA compañía: reconciliar asientos de
        # compañías distintas falla en Odoo
        self.payment_journal = self.env["account.journal"].search(
            [("type", "in", ["cash", "bank"]), ("company_id", "=", company.id)],
            limit=1,
        )
        if not self.payment_journal:
            self.payment_journal = self.env["account.journal"].create(
                {
                    "name": "Cash Journal Test",
                    "code": "CSHT",
                    "type": "cash",
                    "company_id": company.id,
                    "default_credit_account_id": self.bank_account.id,
                    "default_debit_account_id": self.bank_account.id,
                }
            )

        self.main_company = company
        self.expense_journal = self.env["account.journal"].create(
            {
                "name": "Purchase Journal - Test",
                "code": "HRTPJ",
                "type": "purchase",
                "company_id": company.id,
            }
        )

        self.expense_sheet = self.env["hr.expense.sheet"].create(
            {
                "employee_id": self.employee.id,
                "name": "Expense test",
                "journal_id": self.expense_journal.id,
            }
        )
        self.expense_sheet.approve_expense_sheets()

        # Se reutiliza un producto existente: crear plantillas de producto
        # falla en esta BD por una columna NOT NULL residual (sale_line_warn)
        # de un módulo ya desinstalado
        self.product = self.env["product.product"].search([], limit=1)
        if not self.product:
            self.product = self.env["product.product"].browse(1)
        self.product.property_account_expense_id = self.expense_account

        self.expense = self.env["hr.expense"].create(
            {
                "name": "Expense test",
                "employee_id": self.employee.id,
                "product_id": self.product.id,
                "unit_amount": 1,
                "quantity": 10,
                "sheet_id": self.expense_sheet.id,
            }
        )
        self.expense._onchange_product_id()

    def _get_payment_wizard(self):
        ctx = dict(active_ids=self.expense_sheet.ids, active_model="hr.expense.sheet")
        wizard_obj = self.env["hr.expense.sheet.register.payment.wizard"]
        p_methods = self.payment_journal.outbound_payment_method_ids
        ctx.update(default_payment_type="inbound")
        return wizard_obj.with_context(ctx).create(
            {
                "journal_id": self.payment_journal.id,
                "amount": self.expense_sheet.total_amount,
                "payment_method_id": p_methods and p_methods[0].id or False,
                "expense_sheet_id": self.expense_sheet.id,
                "partner_id": self.partner.id,
            }
        )

    def test_post_init_hook(self):
        self.expense_sheet.action_sheet_move_create()
        payment_wizard = self._get_payment_wizard()
        payment_wizard.expense_post_payment()

        payment = self.payment_obj.search(
            [("expense_sheet_id", "=", self.expense_sheet.id)]
        )
        self.assertEqual(len(payment), 1)

        payment.expense_sheet_id = False

        payment = self.payment_obj.search(
            [("expense_sheet_id", "=", self.expense_sheet.id)]
        )
        self.assertFalse(payment)

        post_init_hook(self.env.cr, self.registry)

        payment = self.payment_obj.search(
            [("expense_sheet_id", "=", self.expense_sheet.id)]
        )
        self.assertEqual(len(payment), 1)

    def test_get_payment_vals(self):
        self.expense_sheet.action_sheet_move_create()

        payment_wizard = self._get_payment_wizard()

        payment = self.payment_obj.search(
            [("expense_sheet_id", "=", self.expense_sheet.id)]
        )
        self.assertFalse(payment)

        payment_wizard.expense_post_payment()
        payment = self.payment_obj.search(
            [("expense_sheet_id", "=", self.expense_sheet.id)]
        )
        self.assertEqual(len(payment), 1)

    def test_action_sheet_move_create(self):
        self.expense.payment_mode = "company_account"

        payment = self.payment_obj.search(
            [("expense_sheet_id", "=", self.expense_sheet.id)]
        )
        self.assertFalse(payment)

        self.expense_sheet.action_sheet_move_create()
        payment = self.payment_obj.search(
            [("expense_sheet_id", "=", self.expense_sheet.id)]
        )
        self.assertEqual(len(payment), 1)

    def test_action_cancel_posted(self):
        """Cancelar un reporte publicado genera reverso sin borrar asientos."""
        self.expense_sheet.action_sheet_move_create()
        original_move = self.expense_sheet.account_move_id
        self.assertTrue(original_move)

        self.expense_sheet.action_cancel()

        # El asiento original se conserva publicado (auditoría)
        self.assertTrue(original_move.exists())
        self.assertEqual(original_move.state, "posted")
        # Se creó el asiento de reverso y se vinculó al reporte
        self.assertTrue(self.expense_sheet.reversal_move_id)
        self.assertEqual(self.expense_sheet.reversed_move_id, original_move)
        self.assertFalse(self.expense_sheet.account_move_id)
        self.assertEqual(self.expense_sheet.state, "approve")
        # Los apuntes del original y del reverso quedan conciliados
        self.assertTrue(
            any(line.reconciled for line in original_move.line_ids),
            "Original move lines should be reconciled with the reversal",
        )

    def test_action_cancel_company_account(self):
        """Pagos de la compañía: se cancelan sin borrarse; asiento revertido."""
        self.expense.payment_mode = "company_account"
        self.expense_sheet.action_sheet_move_create()
        original_move = self.expense_sheet.account_move_id

        payment = self.payment_obj.search(
            [("expense_sheet_id", "=", self.expense_sheet.id)]
        )
        self.assertEqual(len(payment), 1)
        self.assertTrue(self.expense_sheet.account_move_id)

        self.expense_sheet.action_cancel()

        # El pago sigue existiendo pero cancelado (no se borra)
        payment = self.payment_obj.search(
            [("expense_sheet_id", "=", self.expense_sheet.id)]
        )
        self.assertEqual(len(payment), 1)
        self.assertEqual(payment.state, "cancelled")
        # Asiento original conservado + reverso generado
        self.assertTrue(original_move.exists())
        self.assertEqual(original_move.state, "posted")
        self.assertTrue(self.expense_sheet.reversal_move_id)
        self.assertFalse(self.expense_sheet.account_move_id)

    def test_action_cancel_own_account(self):
        """Pago directo al empleado: pago cancelado, asientos conservados."""
        self.expense_sheet.action_sheet_move_create()
        original_move = self.expense_sheet.account_move_id

        payment_wizard = self._get_payment_wizard()
        payment_wizard.expense_post_payment()

        payment = self.payment_obj.search(
            [("expense_sheet_id", "=", self.expense_sheet.id)]
        )
        self.assertEqual(len(payment), 1)
        payment_move = payment.move_line_ids.mapped("move_id")
        self.assertEqual(len(payment_move), 1)

        self.expense_sheet.action_cancel()

        # El pago se conserva en estado cancelado (sin unlink)
        payment = self.payment_obj.search(
            [("expense_sheet_id", "=", self.expense_sheet.id)]
        )
        self.assertEqual(len(payment), 1)
        self.assertEqual(payment.state, "cancelled")
        # El asiento del pago también se conserva en estado 'cancel'
        self.assertTrue(payment_move.exists())
        self.assertEqual(payment_move.state, "cancel")
        # Asiento de gasto original conservado + reverso
        self.assertTrue(original_move.exists())
        self.assertEqual(original_move.state, "posted")
        self.assertTrue(self.expense_sheet.reversal_move_id)
        self.assertFalse(self.expense_sheet.account_move_id)

    def test_action_cancel_hook_blocks(self):
        """El hook `_check_cancel_allowed` puede bloquear la cancelación."""
        from odoo.exceptions import UserError

        self.expense_sheet.action_sheet_move_create()

        def _raise(self):
            raise UserError("Blocked by test")

        self.patch(type(self.expense_sheet), "_check_cancel_allowed", _raise)
        with self.assertRaises(UserError):
            self.expense_sheet.action_cancel()
