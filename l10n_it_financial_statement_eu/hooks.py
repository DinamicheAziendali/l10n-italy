from openupgradelib import openupgrade
from openupgradelib.openupgrade import logged_query

from odoo.tools import DotDict

NEW_MODULE_NAME = "l10n_it_financial_statement_eu"
OLD_MODULE_NAME = "l10n_it_account_balance_eu"

RENAMED_MODELS = [
    (
        "account.balance.eu",
        "financial.statement.eu",
    ),
    (
        "account.balance.eu.log",
        "financial.statement.eu.log",
    ),
    (
        "account.balance.eu.wizard",
        "financial.statement.eu.wizard",
    ),
    (
        "report.l10n_it_account_balance_eu.balance_eu_xlsx_report",
        "report.l10n_it_financial_statement_eu.fseu_xlsx_report",
    ),
    (
        "report.l10n_it_account_balance_eu.balance_eu_xbrl_report",
        "report.l10n_it_financial_statement_eu.fseu_xbrl_report",
    ),
    (
        "report.l10n_it_account_balance_eu.balance_eu_html_report",
        "report.l10n_it_financial_statement_eu.fseu_html_report",
    ),
]

RENAMED_FIELDS = [
    (
        "balance_id",
        "financial_statement_id",
    ),
]

RENAMED_XMLIDS = [
    (
        "template_account_balance_report",
        "fseu_html_report",
    ),
]


def remove_models(cr, model_spec):
    for name in model_spec:
        logged_query(
            cr,
            "DELETE FROM ir_model WHERE model = %s",
            (name,),
        )


def migrate_old_module(cr):
    openupgrade.rename_models(
        cr,
        RENAMED_MODELS,
    )
    openupgrade.rename_fields(
        # The method only needs the cursor, not the whole Environment
        DotDict(
            cr=cr,
        ),
        RENAMED_FIELDS,
        # Prevent Environment usage
        # whenever it will be implemented.
        no_deep=True,
    )
    full_renamed_xmlids = [
        (
            ".".join((NEW_MODULE_NAME, old_xmlid)),
            ".".join((NEW_MODULE_NAME, new_xmlid)),
        )
        for old_xmlid, new_xmlid in RENAMED_XMLIDS
    ]
    openupgrade.rename_xmlids(
        cr,
        full_renamed_xmlids,
    )


def pre_absorb_old_module(cr):
    if openupgrade.is_module_installed(cr, OLD_MODULE_NAME):
        openupgrade.update_module_names(
            cr,
            [
                (OLD_MODULE_NAME, NEW_MODULE_NAME),
            ],
            merge_modules=True,
        )
        migrate_old_module(cr)
