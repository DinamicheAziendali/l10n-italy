# Copyright 2019 Simone Rubino - Agile Business Group
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

from odoo import fields, models


class ProductCategory(models.Model):
    _inherit = "product.category"

    l10n_it_intrastat_code_id = fields.Many2one(
        "report.intrastat.code", string="Nomenclature Code"
    )
    intrastat_country_origin_id = fields.Many2one(
        "res.country", string="Origin Country"
    )
    intrastat_type = fields.Selection(
        [
            ("good", "Goods"),
            ("service", "Service"),
            ("misc", "Miscellaneous"),
            ("exclude", "Exclude"),
        ],
    )


class ProductTemplate(models.Model):
    _inherit = "product.template"

    l10n_it_intrastat_code_id = fields.Many2one(
        comodel_name="report.intrastat.code", string="Intrastat Code"
    )
    intrastat_country_origin_id = fields.Many2one(
        "res.country", string="Origin Country"
    )
    intrastat_type = fields.Selection(
        selection=[
            ("good", "Goods"),
            ("service", "Service"),
            ("misc", "Miscellaneous"),
            ("exclude", "Exclude"),
        ],
    )

    def get_intrastat_data(self):
        """
        The intrastat code with the following priority:

        - Intrastat Code on product template
        - Intrastat Code on product category
        """
        res = {
            "l10n_it_intrastat_code_id": False,
            "intrastat_country_origin_id": False,
            "intrastat_type": False,
        }
        # From Product
        if self.intrastat_type:
            res["l10n_it_intrastat_code_id"] = self.l10n_it_intrastat_code_id.id
            res["intrastat_country_origin_id"] = self.intrastat_country_origin_id.id
            res["intrastat_type"] = self.intrastat_type
        elif self.categ_id and self.categ_id.l10n_it_intrastat_code_id:
            res["l10n_it_intrastat_code_id"] = self.categ_id.l10n_it_intrastat_code_id.id
            res[
                "intrastat_country_origin_id"
            ] = self.categ_id.intrastat_country_origin_id.id
            res["intrastat_type"] = self.categ_id.intrastat_type
        return res
