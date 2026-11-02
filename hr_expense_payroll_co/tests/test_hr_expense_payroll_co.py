# Copyright 2026
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl.html).

from odoo.addons.hr_expense_payroll.tests.common import TestExpensePayrollCommon


class TestHrExpensePayrollCo(TestExpensePayrollCommon):
    def setUp(self):
        super().setUp()
        # Nómina con la estructura salarial colombiana completa
        self.contract.struct_id = self.env.ref(
            "l10n_co_hr_payroll_community.structure_co_base"
        )

    def _category_total(self, payslip, code):
        """Suma las líneas de una categoría (incluyendo subcategorías),
        igual que hace el motor de reglas al acumular categories.X."""
        total = 0.0
        for line in payslip.line_ids:
            category = line.category_id
            while category:
                if category.code == code:
                    total += line.total
                    break
                category = category.parent_id
        return total

    def test_net_includes_reimbursement_not_bases(self):
        """El reembolso entra al NET colombiano pero no a las bases."""
        sheet = self._create_sheet(channel="payroll", amount=100.0)
        payslip = self._create_payslip()
        payslip.compute_sheet()

        reimb_line = payslip.line_ids.filtered(lambda l: l.code == "EXP_REIMB")
        self.assertEqual(reimb_line.total, 100.0)

        # NET = GROSS + DED_CO + REIMB (parche aplicado)
        net_line = payslip.line_ids.filtered(lambda l: l.code == "NET")
        gross_line = payslip.line_ids.filtered(lambda l: l.code == "GROSS")
        self.assertTrue(net_line and gross_line)
        expected_net = (
            gross_line.total
            + self._category_total(payslip, "DED_CO")
            + self._category_total(payslip, "REIMB")
        )
        self.assertAlmostEqual(net_line.total, expected_net)

        # La base prestacional NO incluye el reembolso (sólo BASIC + HE)
        prestacionales = payslip.line_ids.filtered(
            lambda l: l.code == "PRESTACIONALES"
        )
        expected_prestacionales = (
            self._category_total(payslip, "BASIC")
            + self._category_total(payslip, "HORAS_EXTRAS")
        )
        self.assertAlmostEqual(prestacionales.total, expected_prestacionales)
        # Si el reembolso hubiera entrado a la base, sería 100 mayor
        self.assertNotAlmostEqual(
            prestacionales.total, expected_prestacionales + 100.0
        )

    def test_no_reimbursement_without_input(self):
        """Sin gastos de canal nómina, la regla EXP_REIMB no genera línea."""
        payslip = self._create_payslip()
        payslip.compute_sheet()

        self.assertFalse(
            payslip.line_ids.filtered(lambda l: l.code == "EXP_REIMB")
        )
        net_line = payslip.line_ids.filtered(lambda l: l.code == "NET")
        gross_line = payslip.line_ids.filtered(lambda l: l.code == "GROSS")
        expected_net = gross_line.total + self._category_total(
            payslip, "DED_CO"
        )
        self.assertAlmostEqual(net_line.total, expected_net)
