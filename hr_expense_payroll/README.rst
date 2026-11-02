==========================
HR Expense Payroll Bridge
==========================

.. |badge1| image:: https://img.shields.io/badge/maturity-Beta-yellow.png
    :target: https://odoo-community.org/page/development-status
    :alt: Beta
.. |badge2| image:: https://img.shields.io/badge/licence-AGPL--3-blue.png
    :target: http://www.gnu.org/licenses/agpl-3.0-standalone.html
    :alt: License: AGPL-3

|badge1| |badge2|

This module bridges *Expenses* and *Payroll* so that expense reports paid by
the employee can be **reimbursed through the payslip**, in addition to the
standard direct payment (bank/cash).

Key features:

* **Two coexisting payment channels** per expense report: *Direct Payment*
  (standard *Register Payment* flow) or *Payroll* (paid in the payslip).
  Mutual exclusions prevent double payments.
* When computing a payslip, the pending balance of the employee's expense
  reports configured for payroll is injected as an ``EXP_REIMB`` input and
  computed by the ``EXP_REIMB`` salary rule.
* On payslip confirmation, the employee payable journal item is **reconciled
  with the expense report journal entry**, and the report is marked as paid
  when the balance reaches zero. Partial reimbursements across periods are
  supported (the pending balance is carried over to the next payslip).
* On payslip cancellation, the reconciliation is released, the report is
  reopened, and the payslip journal entry is **reversed (not deleted)**.
* The reimbursement rule belongs to its own ``REIMB`` category, which does
  not participate in any social security contribution base (works out of the
  box with the Colombian localization).
* Compatible with employee advances:

  - *Expense advances* (``hr_expense_advance_clearing``): netted inside the
    expense flow; only the residual is reimbursed.
  - *Salary advances* (``ohrms_salary_advance``): deducted in the same
    payslip (``SAR`` input), netted automatically against the reimbursement.

**Table of contents**

.. contents::
   :local:

Configuration
=============

#. Install ``hr_payroll_account_community`` (required: salary rules post
   journal entries with it).
#. The *Expense Reimbursement* rule (``EXP_REIMB``) is available in every
   salary structure automatically. Its *Debit Account* is set on installation
   to a default company payable account; you can leave it as is, because on
   payslip confirmation the journal item is rewritten to each employee's
   real payable account (from their home address).
#. The salary journal used by the payslip must have its *Default Credit
   Account* configured (bank account) so the reimbursement cash-out is
   balanced correctly.
#. Each employee needs a *Private Address* (home address) so both the
   expense entry and the payslip entry use the same payable partner.
#. Optional - expense advances: install ``hr_expense_advance_clearing`` to
   net company advances against expenses before reimbursing the residual.
#. Optional - salary advances: install ``ohrms_salary_advance`` to deduct
   approved salary advances in the same payslip.

Usage
=====

#. Go to *Expenses* and create an expense report paid by the employee
   (*Paid By: Employee (to reimburse)*).
#. Set the field *Payment Channel* to *Payroll* (default is
   *Direct Payment*).
#. Submit, approve and *Post Journal Entries* as usual.
#. In *Payroll*, create (or compute) the employee payslip for the period.
   The pending balance of payroll-channel reports is added automatically as
   an ``EXP_REIMB`` input and computed by the *Expense Reimbursement* rule.
#. Confirm the payslip (*Compute Sheet* → *Confirm*):

   - The reimbursement journal item is adjusted to the employee's real
     payable account and commercial partner.
   - It is reconciled with the expense report journal entry.
   - The report is marked as *Done* when fully reimbursed.

#. If the payslip is cancelled (set to draft, then *Cancel*), the
   reconciliation is released, the expense report is reopened and the payslip
   journal entry is reversed (kept for audit).

Notes:

* Expense reports on the payroll channel hide the *Register Payment* button;
  the direct payment wizard refuses them.
* The payment channel cannot be changed once the report has been (partially)
  reimbursed.
* Credit-note payslips never include reimbursements; to undo a reimbursement
  cancel the payslip instead.
* Expense reports dated after the payslip cut-off date are reimbursed in the
  next period automatically.

Bug Tracker
===========

Bugs are tracked on `GitHub Issues <https://github.com/OCA/hr-expense/issues>`_.
In case of trouble, please check there if your issue has already been reported.

Credits
=======

Authors
~~~~~~~

* Custom Addons

Contributors
~~~~~~~~~~~~

* Custom Addons
