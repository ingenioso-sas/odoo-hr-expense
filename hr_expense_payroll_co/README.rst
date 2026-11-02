=====================================
HR Expense Payroll Bridge - Colombia
=====================================

.. |badge1| image:: https://img.shields.io/badge/maturity-Beta-yellow.png
    :target: https://odoo-community.org/page/development-status
    :alt: Beta
.. |badge2| image:: https://img.shields.io/badge/licence-AGPL--3-blue.png
    :target: http://www.gnu.org/licenses/agpl-3.0-standalone.html
    :alt: License: AGPL-3

|badge1| |badge2|

This module adapts the *HR Expense Payroll Bridge* to the **Colombian payroll
localization** (``l10n_co_hr_payroll_community``).

It patches the *Neto a Pagar* (``NET``) salary rule so that the expense
reimbursement (``REIMB`` category) is included in the payslip net amount
printed on reports.

The reimbursement **does not** affect any social security contribution base:
the Colombian rules *Total Devengado* (``GROSS``), *Base Prestacional* and
*IBC* only sum ``BASIC`` + ``DEV`` + overtime categories, and the ``REIMB``
category is not part of them.

**Table of contents**

.. contents::
   :local:

Configuration
=============

Just install it. The patch is applied automatically to the *Neto a Pagar*
(``NET``) rule of the Colombian localization.

No additional configuration is required beyond the one described in the
``hr_expense_payroll`` module.

Usage
=====

#. Configure an expense report with *Payment Channel: Payroll* as described
   in the ``hr_expense_payroll`` usage.
#. Compute and confirm the payslip.
#. Open the payslip report (*Print* → *Payslip*): the *Neto a Pagar* line now
   includes the *Expense Reimbursement* amount, while the contribution bases
   (*IBC*, *Total Devengado*) remain unchanged.

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
