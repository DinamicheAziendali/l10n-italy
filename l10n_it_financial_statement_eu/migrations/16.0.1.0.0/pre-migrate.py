
from odoo.addons.l10n_it_financial_statements_eu import hooks


def migrate(cr, installed_version):
    # Used by OpenUpgrade when module is in `apriori`
    hooks.migrate_old_module(cr)
