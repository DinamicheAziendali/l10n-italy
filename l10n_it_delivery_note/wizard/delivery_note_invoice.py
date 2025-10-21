# Copyright (C) 2018-Today:
# Dinamiche Aziendali Srl (<http://www.dinamicheaziendali.it/>)
# @author: Giuseppe Borruso <gborruso@dinamicheaziendali.it>
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import api, fields, models

INVOICE_STATUSES = [
    ("no", "Nothing to invoice"),
    ("to invoice", "To invoice"),
    ("invoiced", "Fully invoiced"),
]
DOMAIN_INVOICE_STATUSES = [s[0] for s in INVOICE_STATUSES]


class StockDeliveryNoteInvoiceWizard(models.TransientModel):
    _name = "stock.delivery.note.invoice.wizard"
    _description = "Delivery Note Invoice"

    @api.model
    def _get_default_invoice_date(self):
        return fields.Date.context_today(self)

    invoice_date = fields.Date(
        string="Invoice/Bill Date", default=_get_default_invoice_date
    )
    invoice_method = fields.Selection(
        [("dn", "Only DN"), ("service", "With Service")],
        default="dn",
        required=True,
    )

    def create_invoices(self):
        delivery_note_ids = self.env["stock.delivery.note"].browse(
            self._context.get("active_ids", [])
        )
        delivery_note_ids.action_invoice(self.invoice_method)
        invoices = delivery_note_ids.mapped("invoice_ids")
        for invoice in invoices:
            invoice.invoice_date = self.invoice_date

        action_ref = "account.action_move_out_invoice_type"
        action = self.env["ir.actions.actions"]._for_xml_id(action_ref)
        action["domain"] = [("id", "in", invoices.ids)]
        return action
