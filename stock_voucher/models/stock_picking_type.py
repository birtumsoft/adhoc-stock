from odoo import fields, models


class StockPickingType(models.Model):
    _inherit = "stock.picking.type"

    report_signature_section = fields.Boolean(
        string="Añadir sección firma",
        help="Agregar al reporte una sección para firma de recepción.",
        default=False,
    )
