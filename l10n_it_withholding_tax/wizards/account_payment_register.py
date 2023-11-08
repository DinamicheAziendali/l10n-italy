#  Copyright 2023 Simone Rubino - TAKOBI
#  License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from odoo import api, models
from odoo.tools import float_is_zero


class AccountPaymentRegister(models.TransientModel):
    _inherit = "account.payment.register"

    @api.model
    def _get_wizard_values_from_batch(self, batch_result):
        wizard_values_from_batch = super()._get_wizard_values_from_batch(batch_result)
        net_pay_residual_amount = self._compute_withholding_net_pay_residual()
        if net_pay_residual_amount:
            wizard_values_from_batch["source_amount"] = net_pay_residual_amount
            wizard_values_from_batch["source_amount_currency"] = net_pay_residual_amount
        return wizard_values_from_batch

    def _get_total_amount_using_same_currency(
        self, batch_result, early_payment_discount=True
    ):
        amount, mode = super()._get_total_amount_using_same_currency(
            batch_result, early_payment_discount
        )
        net_pay_residual_amount = self._compute_withholding_net_pay_residual()
        if net_pay_residual_amount:
            return net_pay_residual_amount, mode
        return amount, mode

    def _compute_withholding_net_pay_residual(self):
        """If the payment is for Invoices having Withholding Taxes,
        set the Residual Net To Pay as the amount to be paid.
        """
        if self.env.context.get("active_model") == "account.move":
            moves_ids = self.env.context.get("active_ids", [])
            moves = self.env["account.move"].browse(moves_ids)
            withholding_moves = moves.filtered("withholding_tax")
            if withholding_moves:
                net_pay_residual_amount = sum(
                    withholding_moves.mapped("amount_net_pay_residual")
                )
                residual_amount_precision = self.env["decimal.precision"].precision_get(
                    "Account"
                )
                if not float_is_zero(
                    net_pay_residual_amount,
                    precision_digits=residual_amount_precision,
                ):
                    return net_pay_residual_amount
        return False
