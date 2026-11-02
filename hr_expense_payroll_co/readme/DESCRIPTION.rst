This module adapts the *HR Expense Payroll Bridge* to the **Colombian payroll
localization** (``l10n_co_hr_payroll_community``).

It patches the *Neto a Pagar* (``NET``) salary rule so that the expense
reimbursement (``REIMB`` category) is included in the payslip net amount
printed on reports.

The reimbursement **does not** affect any social security contribution base:
the Colombian rules *Total Devengado* (``GROSS``), *Base Prestacional* and
*IBC* only sum ``BASIC`` + ``DEV`` + overtime categories, and the ``REIMB``
category is not part of them.
