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
