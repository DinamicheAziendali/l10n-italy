# Copyright 2026 Nextev Srl
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

from openupgradelib import openupgrade
from psycopg2 import sql

OLD_MODULES = [
    "l10n_it_declaration_of_intent",
]


# Table and model name constants for migration
_OLD_TABLE = "l10n_it_declaration_of_intent_declaration"
_NEW_TABLE = "l10n_it_edi_doi_declaration_of_intent"
_OLD_MODEL = "l10n_it_declaration_of_intent.declaration"
_NEW_MODEL = "l10n_it_edi_doi.declaration_of_intent"


_REL_TABLE = "account_move_l10n_it_declaration_of_intent_declaration_rel"


def _get_rel_table_name(env):
    """Return the old m2m relation table name if it exists, else None."""
    if openupgrade.table_exists(env.cr, _REL_TABLE):
        return _REL_TABLE
    return None


def _migrate_old_declarations_into_new(env):
    """INSERT old declaration records into the new table created by l10n_it_edi_doi.

    A temporary old_id column tracks the old→new ID mapping so that all
    relation/reference tables can be updated with a JOIN instead of arithmetic
    offsets. The sequence is managed automatically by the INSERT.
    """
    # Ensure extension-only columns and the temporary old_id tracker exist
    # (l10n_it_edi_doi_extension hasn't init'd yet at this point)
    for col, col_type in (
        ("type", "varchar"),
        ("number", "varchar"),
        ("old_id", "integer"),
    ):
        if not openupgrade.column_exists(env.cr, _NEW_TABLE, col):
            openupgrade.logged_query(
                env.cr,
                sql.SQL("ALTER TABLE {} ADD COLUMN {} {}").format(
                    sql.Identifier(_NEW_TABLE),
                    sql.Identifier(col),
                    sql.SQL(col_type),
                ),
            )

    # Insert old records; sequence assigns new IDs, old ID is stored in old_id
    openupgrade.logged_query(
        env.cr,
        sql.SQL("""
            INSERT INTO {new_table}
                (old_id, partner_id, company_id, currency_id,
                 issue_date, start_date, end_date, threshold,
                 protocol_number_part1, protocol_number_part2,
                 state, type, number,
                 invoiced, not_yet_invoiced, remaining,
                 create_uid, create_date, write_uid, write_date)
            SELECT
                old.id,
                old.partner_id, old.company_id, old.currency_id,
                old.date, old.date_start, old.date_end, old.limit_amount,
                SPLIT_PART(
                    SPLIT_PART(COALESCE(old.telematic_protocol, ''), '-', 1),
                    '/', 1
                ),
                CASE
                    WHEN old.telematic_protocol LIKE '%%-%%'
                        THEN SPLIT_PART(old.telematic_protocol, '-', 2)
                    WHEN old.telematic_protocol LIKE '%%/%%'
                        THEN SPLIT_PART(old.telematic_protocol, '/', 2)
                    ELSE ''
                END,
                CASE old.state
                    WHEN 'valid' THEN 'active'
                    WHEN 'expired' THEN 'terminated'
                    WHEN 'close' THEN 'revoked'
                    ELSE old.state
                END,
                COALESCE(old.type, 'in'),
                old.number,
                COALESCE(old.used_amount, 0),
                0,
                old.limit_amount - COALESCE(old.used_amount, 0),
                old.create_uid, old.create_date, old.write_uid, old.write_date
            FROM {old_table} old
        """).format(
            new_table=sql.Identifier(_NEW_TABLE),
            old_table=sql.Identifier(_OLD_TABLE),
        ),
    )

    # Update many2many relation table using old_id mapping
    rel_table = _get_rel_table_name(env)
    if rel_table:
        # Drop FK constraints pointing to the old table before updating IDs.
        # The rel table's FK references l10n_it_declaration_of_intent_declaration,
        # but we're setting values that exist only in
        # l10n_it_edi_doi_declaration_of_intent.
        env.cr.execute(
            """
            SELECT conname FROM pg_constraint c
            JOIN pg_class t ON t.oid = c.conrelid
            JOIN pg_class f ON f.oid = c.confrelid
            WHERE t.relname = %s AND f.relname = %s AND c.contype = 'f'
            """,
            (rel_table, _OLD_TABLE),
        )
        for (conname,) in env.cr.fetchall():
            openupgrade.logged_query(
                env.cr,
                sql.SQL("ALTER TABLE {} DROP CONSTRAINT {}").format(
                    sql.Identifier(rel_table),
                    sql.Identifier(conname),
                ),
            )

        query = """
            UPDATE {rel_table} rel
            SET l10n_it_declaration_of_intent_declaration_id = new.id
            FROM {new_table} new
            WHERE rel.l10n_it_declaration_of_intent_declaration_id = new.old_id
            AND NOT EXISTS (
                SELECT 1
                FROM {rel_table} rel_existing
                WHERE rel_existing.account_move_id = rel.account_move_id
                AND rel_existing.l10n_it_declaration_of_intent_declaration_id = new.id
            )
        """
        openupgrade.logged_query(
            env.cr,
            sql.SQL(query).format(
                rel_table=sql.Identifier(rel_table),
                new_table=sql.Identifier(_NEW_TABLE),
            ),
        )

    # Update all model references with new model name, using old_id for matching
    _model_refs = [
        ("ir_model_data", "model", "res_id"),
        ("ir_attachment", "res_model", "res_id"),
    ]
    _optional_model_refs = [
        ("mail_message", "model", "res_id"),
        ("mail_followers", "res_model", "res_id"),
    ]
    for table, model_col, id_col in _model_refs + [
        r for r in _optional_model_refs if openupgrade.table_exists(env.cr, r[0])
    ]:
        openupgrade.logged_query(
            env.cr,
            sql.SQL("""
                UPDATE {table} ref
                SET {model_col} = %s, {id_col} = new.id
                FROM {new_table} new
                WHERE ref.{model_col} = %s AND ref.{id_col} = new.old_id
            """).format(
                table=sql.Identifier(table),
                model_col=sql.Identifier(model_col),
                id_col=sql.Identifier(id_col),
                new_table=sql.Identifier(_NEW_TABLE),
            ),
            (_NEW_MODEL, _OLD_MODEL),
        )

    # Update ir_model_fields.relation (model name only, no record IDs)
    openupgrade.logged_query(
        env.cr,
        """
        UPDATE ir_model_fields
        SET relation = %s
        WHERE relation = %s
        """,
        (_NEW_MODEL, _OLD_MODEL),
    )

    # Clean up old model from ir_model (keep the new one from l10n_it_edi_doi)
    # openupgrade.logged_query(
    #     env.cr,
    #     "DELETE FROM ir_model WHERE model = %s",
    #     (_OLD_MODEL,),
    # )

    # Drop old declaration table (data has been migrated)
    # Note: old_id column is kept until post-migration (used to map IDs
    # when populating account_move_doi from declaration lines).
    # openupgrade.logged_query(
    #     env.cr,
    #     sql.SQL("DROP TABLE IF EXISTS {} CASCADE").format(sql.Identifier(_OLD_TABLE)),
    # )


def _l10n_it_declaration_of_intent_pre_migration(env):
    """
    Migrate data from l10n_it_declaration_of_intent to l10n_it_edi_doi.

    This function handles the migration of:
    - Declaration of Intent records (main model)
    - Many2many relations with account.move
    - State values mapping
    - Database cleanup for Odoo 18 compatibility
    """
    # Check if "l10n_it_declaration_of_intent_declaration" table exists
    if not openupgrade.table_exists(env.cr, _OLD_TABLE):
        # Migration already done or old module never installed
        return

    # Remove views from the old module before Odoo tries to render them.
    # The old module may still be in state 'installed' (not 'to remove'),
    # so Odoo won't clean up its views automatically. They must be deleted
    # here because they use Odoo 16 XPath syntax (e.g. /tree/) that is
    # incompatible with Odoo 18 (renamed to /list/) and would cause a
    # ValueError when opening the invoice form view.
    #
    # The recursive CTE also collects any inherited views that extend
    # the module's views (from any module), so that:
    #  - inherited views are deleted before their parents (no FK violation)
    #  - all ir_model_data rows for deleted views are removed (no orphans)
    openupgrade.logged_query(
        env.cr,
        """
        WITH RECURSIVE views_to_delete AS (
            SELECT v.id
            FROM ir_ui_view v
            JOIN ir_model_data imd
                ON imd.model = 'ir.ui.view'
               AND imd.res_id = v.id
               AND imd.module = 'l10n_it_declaration_of_intent'
            UNION ALL
            SELECT v.id
            FROM ir_ui_view v
            JOIN views_to_delete vtd ON v.inherit_id = vtd.id
        ),
        deleted_imd AS (
            DELETE FROM ir_model_data
            WHERE model = 'ir.ui.view'
              AND res_id IN (SELECT id FROM views_to_delete)
        )
        DELETE FROM ir_ui_view
        WHERE id IN (SELECT id FROM views_to_delete)
        """,
    )

    # Mark old module for removal so Odoo's cleanup handles the rest
    openupgrade.logged_query(
        env.cr,
        """
        UPDATE ir_module_module
        SET state = 'to remove'
        WHERE name = 'l10n_it_declaration_of_intent'
          AND state NOT IN ('uninstalled', 'to remove')
        """,
    )

    # l10n_it_edi_doi (dependency) is always installed first and always
    # creates the new table. Migrate old records into it; the offset ensures
    # no PK conflicts whether the table is empty (offset=0) or not.
    _migrate_old_declarations_into_new(env)

    # Check for the relation table
    rel_table = _get_rel_table_name(env)

    if rel_table:
        # Migrate invoice-DOI links from many2many to many2one
        # In v16, invoices could have multiple DOIs (many2many)
        # In v18, invoices can only have one DOI (many2one)
        # We migrate the first/oldest DOI for each invoice
        openupgrade.logged_query(
            env.cr,
            sql.SQL("""
                UPDATE account_move am
                SET l10n_it_edi_doi_id = subq.doi_id
                FROM (
                    SELECT
                        rel.account_move_id,
                        MIN(rel.l10n_it_declaration_of_intent_declaration_id) as doi_id
                    FROM {rel_table} rel
                    GROUP BY rel.account_move_id
                ) subq
                WHERE am.id = subq.account_move_id
                AND am.l10n_it_edi_doi_id IS NULL
            """).format(rel_table=sql.Identifier(rel_table)),
        )

    # Drop old tables that are no longer needed
    # (lines migrated to account_move_doi in post-migration)
    tables_to_drop = [
        # "l10n_it_declaration_of_intent_yearly_limit",  # Yearly limits
        "account_move_l10n_it_declaration_of_intent_declaration_rel",  # Old M2M
        "move_line_declaration_line_rel",  # Old M2M relation
        "account_tax_l10n_it_declaration_of_intent_declaration_rel",  # Tax↔DOI M2M
        "declaration_select_manually_rel",  # Manually selected DOIs M2M
    ]

    # Drop orphan column on account_move_line (no equivalent in l10n_it_edi_doi)
    if openupgrade.column_exists(
        env.cr, "account_move_line", "force_declaration_of_intent_id"
    ):
        openupgrade.logged_query(
            env.cr,
            "ALTER TABLE account_move_line DROP COLUMN force_declaration_of_intent_id",
        )

    for table in tables_to_drop:
        if openupgrade.table_exists(env.cr, table):
            openupgrade.logged_query(
                env.cr,
                sql.SQL("DROP TABLE IF EXISTS {} CASCADE").format(
                    sql.Identifier(table)
                ),
            )


def _l10n_it_declaration_of_intent_post_migration(env):
    """
    Post-migration tasks for l10n_it_declaration_of_intent.

    This handles data that needs ORM access or depends on loaded modules.
    """
    # Populate l10n_it_edi_doi_amount for all invoices linked to DOI
    # In v18, this field is a stored computed field that calculates the
    # total amount of invoice lines that have the special DOI tax applied.
    # However, in v16, invoices used different taxes
    # (like "Non imponibile iva ART. 8...") and the DOI amount wasn't
    # explicitly tracked.
    #
    # Since we can't recompute using the v18 logic (invoices don't have
    # the v18 DOI tax), we manually populate it with the invoice's
    # untaxed amount. This matches the v16 behavior where the full invoice
    # amount was considered.
    #
    # In v18, l10n_it_edi_doi_amount is always positive regardless of move_type.
    # The v18 compute is: sum(price_total) * -direction_sign
    # Since price_total already has the accounting sign and direction_sign
    # flips it back, the result is always positive.
    # We use ABS(amount_untaxed) as a proxy for migrated invoices.
    openupgrade.logged_query(
        env.cr,
        """
        UPDATE account_move am
        SET l10n_it_edi_doi_amount = ABS(am.amount_untaxed)
        WHERE am.l10n_it_edi_doi_id IS NOT NULL
        AND am.l10n_it_edi_doi_amount = 0
        """,
    )

    # Populate account_move_doi bridge table for multiple DOI support.
    # Source priority:
    # 1. l10n_it_declaration_of_intent_declaration_line: has the real per-invoice
    #    amount (the authoritative source from v16).
    # 2. _REL_TABLE (m2m): no amount, used only if lines were already dropped.
    # 3. l10n_it_edi_doi_id (many2one): last resort if both old tables are gone.
    _LINE_TABLE = "l10n_it_declaration_of_intent_declaration_line"
    if openupgrade.table_exists(env.cr, _LINE_TABLE):
        # Migrate from declaration lines — these carry the real amount per invoice
        openupgrade.logged_query(
            env.cr,
            sql.SQL("""
                INSERT INTO account_move_doi
                    (move_id, declaration_id, amount, sequence,
                     currency_id, company_id,
                     create_uid, create_date, write_uid, write_date)
                SELECT
                    line.invoice_id,
                    new_doi.id,
                    COALESCE(line.amount, 0),
                    ROW_NUMBER() OVER (
                        PARTITION BY line.invoice_id
                        ORDER BY new_doi.id
                    ) * 10,
                    am.currency_id,
                    am.company_id,
                    1, NOW() AT TIME ZONE 'UTC',
                    1, NOW() AT TIME ZONE 'UTC'
                FROM {line_table} line
                JOIN {new_table} new_doi ON new_doi.old_id = line.declaration_id
                JOIN account_move am ON am.id = line.invoice_id
                WHERE line.invoice_id IS NOT NULL
            """).format(
                line_table=sql.Identifier(_LINE_TABLE),
                new_table=sql.Identifier(_NEW_TABLE),
            ),
        )
        # openupgrade.logged_query(
        #     env.cr,
        #     sql.SQL("DROP TABLE IF EXISTS {} CASCADE").format(
        #         sql.Identifier(_LINE_TABLE)
        #     ),
        # )
    else:
        rel_table = _get_rel_table_name(env)
        if rel_table:
            # Lines already gone; fall back to m2m rel table (no real amount)
            openupgrade.logged_query(
                env.cr,
                sql.SQL("""
                    INSERT INTO account_move_doi
                        (move_id, declaration_id, amount, sequence,
                         currency_id, company_id,
                         create_uid, create_date, write_uid, write_date)
                    SELECT
                        rel.account_move_id,
                        rel.l10n_it_declaration_of_intent_declaration_id,
                        0,
                        ROW_NUMBER() OVER (
                            PARTITION BY rel.account_move_id
                            ORDER BY rel.l10n_it_declaration_of_intent_declaration_id
                        ) * 10,
                        am.currency_id,
                        am.company_id,
                        1, NOW() AT TIME ZONE 'UTC',
                        1, NOW() AT TIME ZONE 'UTC'
                    FROM {rel_table} rel
                    JOIN account_move am ON am.id = rel.account_move_id
                """).format(rel_table=sql.Identifier(rel_table)),
            )
            # openupgrade.logged_query(
            #     env.cr,
            #     sql.SQL("DROP TABLE IF EXISTS {} CASCADE").format(
            #         sql.Identifier(rel_table)
            #     ),
            # )
        else:
            # Both old tables gone; create bridge from the many2one field
            openupgrade.logged_query(
                env.cr,
                """
                INSERT INTO account_move_doi
                    (move_id, declaration_id, amount, sequence,
                     currency_id, company_id,
                     create_uid, create_date, write_uid, write_date)
                SELECT
                    am.id,
                    am.l10n_it_edi_doi_id,
                    COALESCE(am.l10n_it_edi_doi_amount, 0),
                    10,
                    am.currency_id,
                    am.company_id,
                    1, NOW() AT TIME ZONE 'UTC',
                    1, NOW() AT TIME ZONE 'UTC'
                FROM account_move am
                WHERE am.l10n_it_edi_doi_id IS NOT NULL
                """,
            )

    # Drop the temporary old_id column now that account_move_doi is populated
    openupgrade.logged_query(
        env.cr,
        sql.SQL("ALTER TABLE {} DROP COLUMN IF EXISTS old_id").format(
            sql.Identifier(_NEW_TABLE)
        ),
    )

    # Update ir.model.data for proper module reference (main DOI model)
    openupgrade.logged_query(
        env.cr,
        """
        UPDATE ir_model_data
        SET module = 'l10n_it_edi_doi_extension'
        WHERE model = 'l10n_it_edi_doi.declaration_of_intent'
        AND module = 'l10n_it_declaration_of_intent'
        """,
    )

    # ---- Clean up all remnants of the old module ----
    openupgrade.logged_query(
        env.cr,
        """
        UPDATE ir_module_module
        SET state = 'installed'
        WHERE name = 'l10n_it_declaration_of_intent' AND state = 'to remove'
        """,
    )
    # old_module = "l10n_it_declaration_of_intent"
    # old_model_prefix = "l10n_it_declaration_of_intent.%"
    #
    # # Delete actions pointing to old models
    # openupgrade.logged_query(
    #     env.cr,
    #     "DELETE FROM ir_act_window WHERE res_model LIKE %s",
    #     (old_model_prefix,),
    # )
    #
    # # Delete menus owned by old module
    # openupgrade.logged_query(
    #     env.cr,
    #     """
    #     DELETE FROM ir_ui_menu m
    #     USING ir_model_data imd
    #     WHERE imd.model = 'ir.ui.menu'
    #       AND imd.res_id = m.id
    #       AND imd.module = %s
    #     """,
    #     (old_module,),
    # )
    #
    # # Delete views owned by old module (if any survived pre-migration)
    # openupgrade.logged_query(
    #     env.cr,
    #     """
    #     DELETE FROM ir_ui_view v
    #     USING ir_model_data imd
    #     WHERE imd.model = 'ir.ui.view'
    #       AND imd.res_id = v.id
    #       AND imd.module = %s
    #     """,
    #     (old_module,),
    # )
    #
    # # Delete access rules for old models
    # openupgrade.logged_query(
    #     env.cr,
    #     """
    #     DELETE FROM ir_model_access
    #     WHERE model_id IN (SELECT id FROM ir_model WHERE model LIKE %s)
    #     """,
    #     (old_model_prefix,),
    # )
    #
    # # Delete record rules for old models
    # openupgrade.logged_query(
    #     env.cr,
    #     """
    #     DELETE FROM ir_rule
    #     WHERE model_id IN (SELECT id FROM ir_model WHERE model LIKE %s)
    #     """,
    #     (old_model_prefix,),
    # )
    #
    # # Delete field selections for old model fields
    # openupgrade.logged_query(
    #     env.cr,
    #     """
    #     DELETE FROM ir_model_fields_selection
    #     WHERE field_id IN (
    #         SELECT id FROM ir_model_fields WHERE model LIKE %s
    #     )
    #     """,
    #     (old_model_prefix,),
    # )
    #
    # # Delete fields belonging to old models
    # openupgrade.logged_query(
    #     env.cr,
    #     "DELETE FROM ir_model_fields WHERE model LIKE %s",
    #     (old_model_prefix,),
    # )
    #
    # # Delete fields added by old module to existing models
    # # (e.g. valid_for_declaration_of_intent on account.fiscal.position)
    # openupgrade.logged_query(
    #     env.cr,
    #     """
    #     DELETE FROM ir_model_fields f
    #     USING ir_model_data imd
    #     WHERE imd.model = 'ir.model.fields'
    #       AND imd.res_id = f.id
    #       AND imd.module = %s
    #       AND f.model NOT LIKE %s
    #     """,
    #     (old_module, old_model_prefix),
    # )
    #
    # # Delete old ir.model records
    # openupgrade.logged_query(
    #     env.cr,
    #     "DELETE FROM ir_model WHERE model LIKE %s",
    #     (old_model_prefix,),
    # )
    #
    # # Delete all remaining ir_model_data for old module
    # openupgrade.logged_query(
    #     env.cr,
    #     "DELETE FROM ir_model_data WHERE module = %s",
    #     (old_module,),
    # )
    #
    # # Remove old module record entirely (already marked 'to remove' in pre-migration)
    # openupgrade.logged_query(
    #     env.cr,
    #     """
    #     DELETE FROM ir_module_module
    #     WHERE name = %s
    #     """,
    #     (old_module,),
    # )


def _l10n_it_edi_doi_extension_pre_init_hook(env):
    for module in OLD_MODULES:
        migration_function = globals().get(f"_{module}_pre_migration")
        if openupgrade.is_module_installed(env.cr, module) and migration_function:
            migration_function(env)


def _l10n_it_edi_doi_extension_post_init_hook(env):
    for module in OLD_MODULES:
        migration_function = globals().get(f"_{module}_post_migration")
        if migration_function:
            env.cr.execute(
                "SELECT state FROM ir_module_module WHERE name = %s", (module,)
            )
            row = env.cr.fetchone()
            # Run post-migration if the old module was installed or is being removed
            # (pre-migration sets state to 'to remove', so is_module_installed = False)
            if row and row[0] in ("installed", "to remove"):
                migration_function(env)
