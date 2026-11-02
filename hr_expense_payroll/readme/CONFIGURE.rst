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
