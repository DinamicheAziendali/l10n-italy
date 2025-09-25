#  Copyright 2025 Giuseppe Borruso - Dinamiche Aziendali srl
#  License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from odoo import Command

from odoo.addons.l10n_it_edi.tests.common import TestItEdi


class TestExportFatturaPAXMLValidation(TestItEdi):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.module = "l10n_it_edi_extension"

    def test_invoice_causale_non_latin(self):
        narration = """
            <p> </p>
            <p>```</p>
            <p>L’impresa è un’attività economica organizzata ai fini della produzione
             o dello scambio di beni o servizi.</p>
            <p>Importo totale fattura è 976,49 €.</p>
            <p>```</p>
        """
        invoice = (
            self.env["account.move"]
            .with_company(self.company)
            .create(
                {
                    "move_type": "out_invoice",
                    "invoice_date": "2022-03-24",
                    "invoice_date_due": "2022-03-24",
                    "partner_id": self.italian_partner_a.id,
                    "narration": narration,
                    "invoice_line_ids": [
                        Command.create(
                            {
                                "name": "line1",
                                "price_unit": 800.40,
                                "tax_ids": [Command.set(self.default_tax.ids)],
                            }
                        ),
                    ],
                }
            )
        )
        invoice.action_post()
        self._assert_export_invoice(invoice, "test_invoice_causale_non_latin.xml")
