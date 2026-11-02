This module allows you to cancel and correct expense reports using **accounting
reversals instead of deleting records**.

It adds a *Reverse* button on the expense sheet that:

* Unlinks the reconciliations between the expense journal entry and any
  related payments.
* Cancels the related payments, keeping them (and their journal entries) for
  audit purposes.
* Creates a **reversal journal entry** (mirror entry) fully reconciled with
  the original expense entry, which is preserved as posted.
* Sets the expense report back to the *Approved* state so it can be posted
  again after being corrected.

.. note::

   This is a behavioral change with respect to the original OCA module: the
   previous version *deleted* payments and journal entries (``unlink`` with
   ``force_delete``), destroying the accounting audit trail. This version
   never deletes accounting records.
