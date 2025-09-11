from openupgradelib import openupgrade

from odoo import SUPERUSER_ID, api

OLD_MODULES = [
    "l10n_it_account_tax_kind",
    "l10n_it_fatturapa",
]


def _l10n_it_account_tax_kind_migration(env):
    if not openupgrade.column_exists(env.cr, "account_tax", "l10n_it_law_reference"):
        field_spec = [
            (
                "l10n_it_law_reference",
                "account.tax",
                "account_tax",
                "char",
                False,
                "l10n_it",
                False,
            )
        ]
        openupgrade.add_fields(env, field_spec)

        query = """
            UPDATE account_tax
            SET l10n_it_law_reference = left(law_reference, 100)
            WHERE law_reference IS NOT NULL
        """
        openupgrade.logged_query(env.cr, query)

    if not openupgrade.column_exists(env.cr, "account_tax", "l10n_it_law_reference"):
        field_spec = [
            (
                "l10n_it_exempt_reason",
                "account.tax",
                "account_tax",
                "char",
                False,
                "l10n_it",
                False,
            )
        ]
        openupgrade.add_fields(env, field_spec)

        query = """
            UPDATE account_tax
            SET l10n_it_exempt_reason = account_tax_kind.code
            FROM account_tax_kind
            WHERE
                account_tax.kind_id = account_tax_kind.id
                AND account_tax.kind_id IS NOT NULL
        """
        openupgrade.logged_query(env.cr, query)


def _l10n_it_fatturapa_migration(env):
    """
    Remove exclusion for installation of "l10n_it_edi"
    """
    query = """
        DELETE
        FROM ir_module_module_exclusion
        WHERE name = 'l10n_it_edi'
    """
    openupgrade.logged_query(env.cr, query)


def migrate(cr, version):
    env = api.Environment(cr, SUPERUSER_ID, {})
    for module in OLD_MODULES:
        migration_function = globals().get(f"_{module}_migration")
        if openupgrade.is_module_installed(env.cr, module) and migration_function:
            migration_function(env)
