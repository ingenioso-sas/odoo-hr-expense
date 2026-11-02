13.0.2.0.0 (2026-10-28)

* **Breaking change**: cancelling an expense report no longer deletes payments
  and journal entries. It now creates accounting reversals and cancels
  payments, preserving the full audit trail.
* The report is set back to *Approved* (instead of *Submitted*) so it can be
  corrected and posted again.
* The button label changed from *Cancel* to *Reverse*.
* New fields on the expense sheet: *Reversed Move* and *Reversal Move*.
* New hook ``_check_cancel_allowed()`` so other modules (e.g. payroll bridge)
  can block the reversal when external links must be released first.
