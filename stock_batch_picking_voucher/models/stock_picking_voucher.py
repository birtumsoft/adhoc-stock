import logging
from odoo import api, fields, models
from odoo.exceptions import ValidationError

_logger = logging.getLogger(__name__)


class StockPickingVoucher(models.Model):
    _inherit = "stock.picking.voucher"

    batch_id = fields.Many2one("stock.picking.batch", "Batch", ondelete="cascade", index=True)
    picking_id = fields.Many2one("stock.picking", "Picking", ondelete="cascade", required=False, index=True)

    @api.constrains("picking_id", "batch_id")
    def _check_picking_id_required(self):
        for record in self:
            _logger.debug("🔍 Verificando voucher (id=%s) picking_id=%s batch_id=%s",
                          record.id, record.picking_id.id, record.batch_id.id)
            if not record.batch_id and not record.picking_id:
                _logger.error("❌ Voucher sin picking ni batch detectado.")
                raise ValidationError(
                    "Al crear un voucher debe estar ligado a una trasnferencia o lote de transferencias"
                )
