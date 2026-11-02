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
