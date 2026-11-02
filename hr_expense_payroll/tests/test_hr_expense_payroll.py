# Copyright 2026
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl.html).

from datetime import timedelta

from odoo.exceptions import UserError

from .common import TestExpensePayrollCommon


class TestHrExpensePayroll(TestExpensePayrollCommon):
    def test_payroll_channel_settles_sheet(self):
        """Flujo completo: canal nómina → input → confirmar → conciliar."""
        sheet = self._create_sheet(channel="payroll", amount=100.0)
        self.assertEqual(sheet.amount_to_pay, 100.0)

        payslip = self._create_payslip()
        payslip.compute_sheet()

        # Input EXP_REIMB con el saldo y snapshot de la hoja
        reimb_input = payslip.input_line_ids.filtered(
            lambda i: i.code == "EXP_REIMB"
        )
        self.assertEqual(len(reimb_input), 1)
        self.assertEqual(reimb_input.amount, 100.0)
        self.assertEqual(payslip.expense_sheet_ids, sheet)
        # Línea de nómina generada la regla
        reimb_line = payslip.line_ids.filtered(lambda l: l.code == "EXP_REIMB")
        self.assertEqual(len(reimb_line), 1)
        self.assertEqual(reimb_line.total, 100.0)

        payslip.action_payslip_done()

        # Reporte pagado y conciliado
        self.assertEqual(sheet.state, "done")
        self.assertEqual(sheet.amount_to_pay, 0.0)
        self.assertIn(payslip, sheet.payslip_ids)
        payable_lines = sheet.account_move_id.line_ids.filtered(
            lambda l: l.account_id == self.payable_account
        )
        self.assertTrue(
            any(line.reconciled for line in payable_lines),
            "Expense payable line should be reconciled with the payslip",
        )

    def test_no_input_for_direct_channel(self):
        """El canal directo no genera reembolsos por nómina."""
        sheet = self._create_sheet(channel="direct", amount=100.0)
        payslip = self._create_payslip()
        payslip.compute_sheet()

        self.assertFalse(
            payslip.input_line_ids.filtered(lambda i: i.code == "EXP_REIMB")
        )
        self.assertFalse(payslip.expense_sheet_ids)
        self.assertFalse(sheet.payslip_ids)

    def test_cut_off_excludes_future_expenses(self):
        """Gastos posteriores al corte de la nómina se pagan en la siguiente."""
        future_date = self.period_to + timedelta(days=1)
        sheet = self._create_sheet(channel="payroll", amount=100.0, date=future_date)

        payslip = self._create_payslip()
        payslip.compute_sheet()
        self.assertFalse(payslip.expense_sheet_ids)

        next_payslip = self._create_payslip(
            date_from=self.period_to + timedelta(days=1),
            date_to=self.period_to + timedelta(days=31),
        )
        next_payslip.compute_sheet()
        self.assertIn(sheet, next_payslip.expense_sheet_ids)

    def test_register_payment_blocked_payroll_channel(self):
        """No se puede registrar pago directo de un reporte de canal nómina."""
        sheet = self._create_sheet(channel="payroll", amount=100.0)
        wizard_obj = self.env["hr.expense.sheet.register.payment.wizard"]
        ctx = {"active_model": "hr.expense.sheet", "active_id": sheet.id}
        with self.assertRaises(UserError):
            wizard_obj.with_context(ctx).default_get(["amount"])

    def test_overpayment_blocked_direct_channel(self):
        """No se puede pagar más del saldo pendiente por el canal directo."""
        sheet = self._create_sheet(channel="direct", amount=100.0)
        wizard_obj = self.env["hr.expense.sheet.register.payment.wizard"]
        ctx = {
            "active_model": "hr.expense.sheet",
            "active_id": sheet.id,
            "active_ids": sheet.ids,
        }
        method = (
            self.payment_journal.outbound_payment_method_ids[:1]
            or self.payment_journal.inbound_payment_method_ids[:1]
        )
        wizard = wizard_obj.with_context(ctx).create(
            {
                "expense_sheet_id": sheet.id,
                "partner_id": self.home_partner.id,
                "journal_id": self.payment_journal.id,
                "amount": 150.0,
                "payment_method_id": method.id if method else False,
            }
        )
        with self.assertRaises(UserError):
            wizard.expense_post_payment()

    def test_channel_change_blocked_after_payment(self):
        """No se puede cambiar el canal una vez pagado el reporte."""
        sheet = self._create_sheet(channel="payroll", amount=100.0)
        payslip = self._create_payslip()
        payslip.compute_sheet()
        payslip.action_payslip_done()
        self.assertEqual(sheet.state, "done")

        with self.assertRaises(UserError):
            sheet.payment_channel = "direct"

    def test_cancel_payslip_reopens_sheet(self):
        """Cancelar la nómina revierte el asiento y reabre el reporte."""
        sheet = self._create_sheet(channel="payroll", amount=100.0)
        payslip = self._create_payslip()
        payslip.compute_sheet()
        payslip.action_payslip_done()
        self.assertTrue(payslip.move_id)

        # El flujo estándar para cancelar una nómina confirmada es
        # volver a borrador y después cancelar
        payslip.action_payslip_draft()
        original_move = payslip.move_id
        self.assertTrue(original_move)

        payslip.action_payslip_cancel()

        self.assertEqual(payslip.state, "cancel")
        self.assertFalse(payslip.move_id)
        self.assertEqual(payslip.reversed_move_id, original_move)
        self.assertTrue(payslip.reversal_move_id)
        self.assertEqual(payslip.reversal_move_id.state, "posted")
        # Reporte reabierto con el saldo pendiente completo
        self.assertEqual(sheet.state, "post")
        self.assertEqual(sheet.amount_to_pay, 100.0)
        self.assertNotIn(payslip, sheet.payslip_ids)

    def test_sheet_cancel_blocked_by_active_payslip(self):
        """No se puede revertir un reporte reembolsado por nómina activa."""
        sheet = self._create_sheet(channel="payroll", amount=100.0)
        payslip = self._create_payslip()
        payslip.compute_sheet()
        payslip.action_payslip_done()

        # La relación reporte↔nómina debe quedar registrada (BD y ORM)
        self.env.cr.execute(
            "SELECT COUNT(*) FROM hr_expense_sheet_payslip_rel "
            "WHERE sheet_id = %s AND payslip_id = %s",
            (sheet.id, payslip.id),
        )
        self.assertEqual(self.env.cr.fetchone()[0], 1)
        self.assertIn(payslip, sheet.payslip_ids)

        with self.assertRaises(UserError):
            sheet.action_cancel()

    def test_credit_note_excludes_reimbursement(self):
        """Las notas crédito no incluyen el input de reembolso."""
        self._create_sheet(channel="payroll", amount=100.0)
        payslip = self._create_payslip(credit_note=True)
        payslip.compute_sheet()
        self.assertFalse(
            payslip.input_line_ids.filtered(lambda i: i.code == "EXP_REIMB")
        )
        self.assertFalse(payslip.expense_sheet_ids)

    def test_fix_move_line_uses_employee_payable(self):
        """La línea de nómina se reajusta a la payable real del empleado."""
        # Otro partner con cuenta payable distinta a la de la regla
        other_partner = self.env["res.partner"].create(
            {
                "name": "Other Employee Home",
                "property_account_payable_id": self.other_payable_account.id,
            }
        )
        self.employee.address_home_id = other_partner
        sheet = self._create_sheet(channel="payroll", amount=80.0)

        payslip = self._create_payslip()
        payslip.compute_sheet()
        payslip.action_payslip_done()

        # El asiento de la nómina usa la payable real del empleado
        self.assertTrue(
            any(
                line.account_id == self.other_payable_account
                for line in payslip.move_id.line_ids
            )
        )
        self.assertEqual(sheet.state, "done")
        self.assertEqual(sheet.amount_to_pay, 0.0)
