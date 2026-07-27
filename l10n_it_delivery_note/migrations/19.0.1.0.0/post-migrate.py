# Copyright 2026 Giuseppe Borruso - Dinamiche Aziendali srl
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl.html).

from openupgradelib import openupgrade

from odoo.addons.l10n_it_delivery_note.hooks import (
    OLD_MODULE,
    _ensure_delivery_note_types,
    _l10n_it_ddt_post_migration,
    _module_state,
)


@openupgrade.migrate()
def migrate(env, version):
    if _module_state(env, OLD_MODULE) not in ("installed", "to remove"):
        return

    _ensure_delivery_note_types(env)
    _l10n_it_ddt_post_migration(env)
