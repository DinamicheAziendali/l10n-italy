# Copyright 2023 Nextev Srl
# Copyright 2026 Giuseppe Borruso - Dinamiche Aziendali srl
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl.html).

import logging

from openupgradelib import openupgrade

from odoo import Command, fields
from odoo.exceptions import UserError

_logger = logging.getLogger(__name__)

OLD_MODULE = "l10n_it_ddt"
OLD_DOCUMENT_TABLE = "stock_picking_package_preparation"
OLD_LINE_TABLE = "stock_picking_package_preparation_line"
OLD_PICKING_REL_TABLE = "stock_picking_pack_prepare_rel"
OLD_LINE_TAX_REL_TABLE = "account_tax_stock_picking_package_preparation_line_rel"

STATES_MAPPING = {
    "draft": "draft",
    "cancel": "cancel",
    "in_pack": "draft",
    "done": "confirm",
}

REFERENCE_MAPPINGS = (
    (
        "stock_picking_carriage_condition",
        "stock.picking.transport.condition",
        (
            ("carriage_condition_PF", "transport_condition_PF"),
            ("carriage_condition_PA", "transport_condition_PA"),
            ("carriage_condition_PAF", "transport_condition_PAF"),
        ),
    ),
    (
        "stock_picking_goods_description",
        "stock.picking.goods.appearance",
        (
            ("goods_description_CAR", "goods_appearance_CAR"),
            ("goods_description_BAN", "goods_appearance_BAN"),
            ("goods_description_SFU", "goods_appearance_SFU"),
            ("goods_description_CBA", "goods_appearance_CBA"),
        ),
    ),
    (
        "stock_picking_transportation_reason",
        "stock.picking.transport.reason",
        (
            ("transportation_reason_VEN", "transport_reason_VEN"),
            ("transportation_reason_VIS", "transport_reason_VIS"),
            ("transportation_reason_RES", "transport_reason_RES"),
        ),
    ),
    (
        "stock_picking_transportation_method",
        "stock.picking.transport.method",
        (
            ("transportation_method_MIT", "transport_method_MIT"),
            ("transportation_method_DES", "transport_method_DES"),
            ("transportation_method_COR", "transport_method_COR"),
        ),
    ),
)


def _module_state(env, module):
    env.cr.execute(
        "SELECT state FROM ir_module_module WHERE name = %s",
        (module,),
    )
    row = env.cr.fetchone()
    return row[0] if row else False


def _xmlid_res_id(env, xmlid):
    module, name = xmlid.split(".", 1)
    env.cr.execute(
        """
        SELECT res_id
        FROM ir_model_data
        WHERE module = %s AND name = %s
        """,
        (module, name),
    )
    row = env.cr.fetchone()
    return row[0] if row else False


def _migrate_reference_records(env):
    """Map standard records and copy user-created shipping configuration."""
    migrated = {}

    for old_table, new_model_name, xmlid_mappings in REFERENCE_MAPPINGS:
        if not openupgrade.table_exists(env.cr, old_table):
            migrated[old_table] = {}
            continue

        records_map = {}
        for old_name, new_name in xmlid_mappings:
            old_id = _xmlid_res_id(env, f"{OLD_MODULE}.{old_name}")
            new_record = env.ref(
                f"l10n_it_delivery_note.{new_name}",
                raise_if_not_found=False,
            )
            if old_id and new_record:
                records_map[old_id] = new_record.id

        env.cr.execute(
            f"""
            SELECT id, name, note
            FROM {old_table}
            ORDER BY id
            """
        )
        NewModel = env[new_model_name]
        for old_id, name, note in env.cr.fetchall():
            if old_id in records_map:
                continue
            new_record = NewModel.search([("name", "=", name)], limit=1)
            if not new_record:
                new_record = NewModel.create(
                    {
                        "name": name,
                        "note": note,
                    }
                )
            records_map[old_id] = new_record.id

        migrated[old_table] = records_map

    return migrated


def _mapped_id(mapping, old_id):
    return mapping.get(old_id) if old_id else False


def _outgoing_type(env, company):
    return env["stock.delivery.note.type"].search(
        [
            ("code", "=", "outgoing"),
            ("print_prices", "=", False),
            ("company_id", "=", company.id),
        ],
        limit=1,
    )


def _migrate_document_types(env, reference_maps):
    """Convert ``stock.ddt.type`` records and preserve their sequences."""
    if not openupgrade.table_exists(env.cr, "stock_ddt_type"):
        return {}

    standard_type_id = _xmlid_res_id(env, f"{OLD_MODULE}.ddt_type_ddt")
    env.cr.execute(
        """
        SELECT
            id,
            name,
            sequence_id,
            note,
            default_carriage_condition_id,
            default_goods_description_id,
            default_transportation_reason_id,
            default_transportation_method_id,
            company_id
        FROM stock_ddt_type
        ORDER BY id
        """
    )

    type_map = {}
    sequence_ids = set()
    for (
        old_id,
        name,
        sequence_id,
        note,
        carriage_condition_id,
        goods_description_id,
        transportation_reason_id,
        transportation_method_id,
        company_id,
    ) in env.cr.fetchall():
        company = env["res.company"].browse(company_id).exists() or env.company
        sequence_ids.add(sequence_id)

        if old_id == standard_type_id:
            new_type = _outgoing_type(env, company)
            if not new_type:
                env["stock.delivery.note.type"].create_dn_types(company)
                new_type = _outgoing_type(env, company)
            env["stock.delivery.note.type"].search(
                [
                    ("code", "=", "outgoing"),
                    ("company_id", "=", company.id),
                ]
            ).write({"sequence_id": sequence_id})
        else:
            values = {
                "name": name,
                "sequence_id": sequence_id,
                "default_goods_appearance_id": _mapped_id(
                    reference_maps["stock_picking_goods_description"],
                    goods_description_id,
                ),
                "default_transport_reason_id": _mapped_id(
                    reference_maps["stock_picking_transportation_reason"],
                    transportation_reason_id,
                ),
                "default_transport_condition_id": _mapped_id(
                    reference_maps["stock_picking_carriage_condition"],
                    carriage_condition_id,
                ),
                "default_transport_method_id": _mapped_id(
                    reference_maps["stock_picking_transportation_method"],
                    transportation_method_id,
                ),
                "note": note,
                "code": "outgoing",
                "company_id": company.id,
            }
            new_type = env["stock.delivery.note.type"].search(
                [
                    ("name", "=", name),
                    ("company_id", "=", company.id),
                ],
                limit=1,
            )
            if new_type:
                new_type.write(values)
            else:
                new_type = env["stock.delivery.note.type"].create(values)

        type_map[old_id] = new_type.id

    # The old module must not delete sequences now used by the new types.
    if sequence_ids:
        openupgrade.logged_query(
            env.cr,
            """
            DELETE FROM ir_model_data
            WHERE
                module = %s
                AND model = 'ir.sequence'
                AND res_id IN %s
            """,
            (OLD_MODULE, tuple(sequence_ids)),
        )

    return type_map


def _migrate_supplier_references(env):
    """Rename the supplier DDT information kept on stock pickings."""
    if not (
        openupgrade.column_exists(env.cr, "stock_picking", "ddt_supplier_number")
        and openupgrade.column_exists(env.cr, "stock_picking", "ddt_supplier_date")
    ):
        return

    openupgrade.logged_query(
        env.cr,
        """
        UPDATE stock_picking
        SET
            dn_supplier_number = ddt_supplier_number,
            dn_supplier_date = ddt_supplier_date
        WHERE
            ddt_supplier_number IS NOT NULL
            OR ddt_supplier_date IS NOT NULL
        """,
    )


def _old_document_pickings(env, old_document_id):
    if not openupgrade.table_exists(env.cr, OLD_PICKING_REL_TABLE):
        return env["stock.picking"]

    env.cr.execute(
        f"""
        SELECT stock_picking_id
        FROM {OLD_PICKING_REL_TABLE}
        WHERE stock_picking_package_preparation_id = %s
        ORDER BY stock_picking_id
        """,
        (old_document_id,),
    )
    return env["stock.picking"].browse([row[0] for row in env.cr.fetchall()]).exists()


def _computed_old_weight(pickings):
    return sum(
        move.product_id.weight * move.quantity
        for move in pickings.move_ids
        if move.state != "cancel"
    )


def _old_invoice_to_move(env, old_invoice_id):
    if not old_invoice_id:
        return env["account.move"]

    if openupgrade.column_exists(env.cr, "account_move", "old_invoice_id"):
        env.cr.execute(
            """
            SELECT id
            FROM account_move
            WHERE old_invoice_id = %s
            LIMIT 1
            """,
            (old_invoice_id,),
        )
        row = env.cr.fetchone()
        if row:
            return env["account.move"].browse(row[0]).exists()

    if openupgrade.table_exists(
        env.cr, "account_invoice"
    ) and openupgrade.column_exists(env.cr, "account_invoice", "move_id"):
        env.cr.execute(
            "SELECT move_id FROM account_invoice WHERE id = %s",
            (old_invoice_id,),
        )
        row = env.cr.fetchone()
        if row:
            move = env["account.move"].browse(row[0]).exists()
            if move:
                return move

    move = env["account.move"].browse(old_invoice_id).exists()
    return move if move and move.move_type != "entry" else env["account.move"]


def _old_line_tax_ids(env, old_line_id):
    if not openupgrade.table_exists(env.cr, OLD_LINE_TAX_REL_TABLE):
        return []

    env.cr.execute(
        f"""
        SELECT account_tax_id
        FROM {OLD_LINE_TAX_REL_TABLE}
        WHERE stock_picking_package_preparation_line_id = %s
        ORDER BY account_tax_id
        """,
        (old_line_id,),
    )
    tax_ids = [row[0] for row in env.cr.fetchall()]
    return env["account.tax"].browse(tax_ids).exists().ids


def _migrate_extra_lines(env, old_document_id, delivery_note):
    if not openupgrade.table_exists(env.cr, OLD_LINE_TABLE):
        return

    env.cr.execute(
        f"""
        SELECT
            id,
            sequence,
            name,
            product_id,
            product_uom_qty,
            product_uom_id,
            price_unit,
            discount
        FROM {OLD_LINE_TABLE}
        WHERE
            package_preparation_id = %s
            AND move_id IS NULL
        ORDER BY sequence, id
        """,
        (old_document_id,),
    )
    lines = env.cr.fetchall()
    if not lines:
        return

    commands = []
    for (
        old_line_id,
        sequence,
        name,
        product_id,
        product_uom_qty,
        product_uom_id,
        price_unit,
        discount,
    ) in lines:
        commands.append(
            Command.create(
                {
                    "sequence": sequence,
                    "name": name,
                    "product_id": product_id,
                    "product_qty": product_uom_qty,
                    "product_uom_id": product_uom_id,
                    "price_unit": price_unit,
                    "currency_id": delivery_note.company_id.currency_id.id,
                    "discount": discount,
                    "tax_ids": [Command.set(_old_line_tax_ids(env, old_line_id))],
                }
            )
        )
    delivery_note.write({"line_ids": commands})


def _migrate_documents(env, reference_maps, type_map):
    if not openupgrade.table_exists(env.cr, OLD_DOCUMENT_TABLE):
        return

    env.cr.execute(f"SELECT COUNT(*) FROM {OLD_DOCUMENT_TABLE}")
    old_document_count = env.cr.fetchone()[0]
    if old_document_count and env["stock.delivery.note"].search_count([]):
        raise UserError(
            env._(
                "The old l10n_it_ddt documents cannot be migrated because "
                "delivery notes already exist in l10n_it_delivery_note."
            )
        )

    env.cr.execute(
        f"""
        SELECT
            id,
            state,
            ddt_number,
            company_id,
            partner_id,
            partner_shipping_id,
            ddt_type_id,
            date,
            carrier_id,
            date_done,
            parcels,
            volume,
            volume_uom_id,
            gross_weight,
            gross_weight_uom_id,
            weight_manual,
            weight_manual_uom_id,
            goods_description_id,
            transportation_reason_id,
            carriage_condition_id,
            transportation_method_id,
            invoice_id,
            note
        FROM {OLD_DOCUMENT_TABLE}
        ORDER BY id
        """
    )
    rows = env.cr.fetchall()

    DeliveryNote = env["stock.delivery.note"]
    for (
        old_id,
        state,
        name,
        company_id,
        partner_id,
        partner_shipping_id,
        old_type_id,
        date,
        carrier_id,
        date_done,
        packages,
        volume,
        volume_uom_id,
        gross_weight,
        gross_weight_uom_id,
        weight_manual,
        net_weight_uom_id,
        goods_description_id,
        transportation_reason_id,
        carriage_condition_id,
        transportation_method_id,
        old_invoice_id,
        note,
    ) in rows:
        company = env["res.company"].browse(company_id).exists() or env.company
        partner = env["res.partner"].browse(partner_id).exists()
        if not partner:
            raise UserError(
                env._(
                    "The old delivery note %(document_id)s has no valid partner.",
                    document_id=old_id,
                )
            )
        shipping_partner = (
            env["res.partner"].browse(partner_shipping_id).exists() or partner
        )
        carrier = env["res.partner"].browse(carrier_id).exists()

        pickings = _old_document_pickings(env, old_id)
        delivery_method = pickings.mapped("carrier_id")[:1]
        if not delivery_method:
            delivery_method = partner.property_delivery_carrier_id

        new_type = (
            env["stock.delivery.note.type"].browse(type_map.get(old_type_id)).exists()
        )
        if not new_type:
            new_type = _outgoing_type(env, company)
        if not new_type:
            raise UserError(
                env._(
                    "No outgoing delivery note type is available for "
                    "company %(company)s.",
                    company=company.display_name,
                )
            )

        computed_weight = _computed_old_weight(pickings)
        invoice = _old_invoice_to_move(env, old_invoice_id)
        default_volume_uom = env.ref(
            "uom.product_uom_litre",
            raise_if_not_found=False,
        )
        default_weight_uom = env.ref(
            "uom.product_uom_kgm",
            raise_if_not_found=False,
        )
        values = {
            "state": STATES_MAPPING.get(state, "draft"),
            "name": name,
            "partner_sender_id": company.partner_id.id,
            "partner_id": partner.id,
            "partner_shipping_id": shipping_partner.id,
            "type_id": new_type.id,
            "sequence_id": new_type.sequence_id.id if name else False,
            "date": fields.Date.to_date(date) if date else False,
            "company_id": company.id,
            "carrier_id": carrier.id,
            "delivery_method_id": delivery_method.id,
            "transport_datetime": date_done,
            "packages": packages,
            "volume": volume,
            "volume_uom_id": volume_uom_id or default_volume_uom.id,
            "gross_weight": gross_weight or computed_weight,
            "gross_weight_uom_id": gross_weight_uom_id or default_weight_uom.id,
            "net_weight": weight_manual or computed_weight,
            "net_weight_uom_id": net_weight_uom_id or default_weight_uom.id,
            "goods_appearance_id": _mapped_id(
                reference_maps["stock_picking_goods_description"],
                goods_description_id,
            ),
            "transport_reason_id": _mapped_id(
                reference_maps["stock_picking_transportation_reason"],
                transportation_reason_id,
            ),
            "transport_condition_id": _mapped_id(
                reference_maps["stock_picking_carriage_condition"],
                carriage_condition_id,
            ),
            "transport_method_id": _mapped_id(
                reference_maps["stock_picking_transportation_method"],
                transportation_method_id,
            ),
            "picking_ids": [Command.set(pickings.ids)],
            "invoice_ids": [Command.set(invoice.ids)],
            "note": note,
        }
        delivery_note = DeliveryNote.with_company(company).create(values)
        _migrate_extra_lines(env, old_id, delivery_note)

    _logger.info("Migrated %s delivery notes from l10n_it_ddt", len(rows))


def _l10n_it_ddt_post_migration(env):
    reference_maps = _migrate_reference_records(env)
    type_map = _migrate_document_types(env, reference_maps)
    _migrate_supplier_references(env)
    _migrate_documents(env, reference_maps, type_map)

    openupgrade.logged_query(
        env.cr,
        """
        UPDATE ir_module_module
        SET state = 'to remove'
        WHERE
            name = %s
            AND state != 'uninstalled'
        """,
        (OLD_MODULE,),
    )


def _ensure_delivery_note_types(env):
    companies = env["res.company"].search([])
    for company in companies:
        env["stock.delivery.note.type"].create_dn_types(company)


def post_init_hook(env):
    """
    Create DN types and migrate data from the obsolete ``l10n_it_ddt`` module.
    """
    _ensure_delivery_note_types(env)

    if _module_state(env, OLD_MODULE) in ("installed", "to remove"):
        _l10n_it_ddt_post_migration(env)
