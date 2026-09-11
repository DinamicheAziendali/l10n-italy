from openupgradelib import openupgrade


@openupgrade.migrate()
def migrate(env, version):
    if openupgrade.is_module_installed(env.cr, "l10n_it_edi_dn"):
        openupgrade.update_module_names(
            env.cr,
            [("l10n_it_edi_dn", "l10n_it_delivery_note")],
            merge_modules=True,
        )
