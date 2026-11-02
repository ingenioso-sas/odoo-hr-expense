# Copyright 2019 Tecnativa - Ernesto Tejeda
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl.html).

from odoo import _, fields, models


class AccountMove(models.Model):
    _inherit = "account.move"

    def _create_reversal_entry(self, date=None):
        """Crea un asiento de reverso (espejo) y lo concilia con el original.

        El asiento original se conserva publicado; el de reverso se publica y
        ambas partes quedan conciliadas, dejando traza contable completa sin
        borrar ni cancelar el registro original.

        :param date: fecha del reverso (por defecto, hoy).
        :return: asiento de reverso creado.
        """
        self.ensure_one()
        line_ids = []
        for line in self.line_ids:
            line_ids.append(
                (
                    0,
                    0,
                    {
                        "name": line.name,
                        "partner_id": line.partner_id.id,
                        "account_id": line.account_id.id,
                        "debit": line.credit,
                        "credit": line.debit,
                        "analytic_account_id": line.analytic_account_id.id,
                        "tax_ids": [(6, 0, line.tax_ids.ids)],
                        "currency_id": (
                            line.currency_id.id
                            if line.currency_id
                            and line.currency_id != line.company_id.currency_id
                            else False
                        ),
                        "amount_currency": -line.amount_currency,
                    },
                )
            )
        reversal = self.create(
            {
                "journal_id": self.journal_id.id,
                "company_id": self.company_id.id,
                "date": date or fields.Date.context_today(self),
                "ref": _("Reversal of %s") % (self.ref or self.name),
                "line_ids": line_ids,
            }
        )
        reversal.post()
        # Concilia el original con el reverso para dejar ambos saldados
        (self.line_ids + reversal.line_ids).filtered(
            lambda l: l.account_id.internal_type in ("receivable", "payable")
            and not l.reconciled
        ).reconcile()
        return reversal
