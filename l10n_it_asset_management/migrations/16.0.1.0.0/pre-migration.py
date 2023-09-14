# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

from openupgradelib import openupgrade


def migrate(cr, installed_version):
    if not installed_version or openupgrade.table_exists(
        cr, "l10n_it_asset_management"
    ):
        return

    openupgrade.rename_tables(cr, [("assets_management", "l10n_it_asset_management")])
