import logging
from odoo import _, api, fields, models
from odoo.exceptions import UserError

_logger = logging.getLogger(__name__)


class StockPickingBatch(models.Model):
    _inherit = "stock.picking.batch"

    voucher_ids = fields.One2many(
        "stock.picking.voucher",
        "batch_id",
        "Remitos",
        copy=False,
    )

    book_id = fields.Many2one("stock.book", "Talonario", copy=False, ondelete="restrict", check_company=True)
    next_number = fields.Integer(related="book_id.next_number")

    def assign_numbers(self, estimated_number_of_pages, book):
        _logger.info("🧾 Asignando %s remitos para batch %s usando talonario %s",
                     estimated_number_of_pages, self.display_name, book.display_name)
        self.ensure_one()
        list_of_vouchers = []
        for page in range(estimated_number_of_pages):
            next_num = book.sequence_id.next_by_id()
            _logger.debug("➡️ Generando número de remito: %s", next_num)
            list_of_vouchers.append({
                "name": next_num,
                "book_id": book.id,
                "batch_id": self.id,
            })
        self.env["stock.picking.voucher"].sudo().create(list_of_vouchers)
        self.message_post(body=_("Números de remitos asignados: %s") % (self.voucher_ids.mapped("display_name")))
        self.write({"book_id": book.id})
        _logger.info("✅ Remitos creados correctamente para batch %s", self.id)

    printed = fields.Boolean()
    with_vouchers = fields.Boolean(compute="_compute_with_vouchers")

    @api.depends("picking_ids", "picking_ids.voucher_ids")
    def _compute_with_vouchers(self):
        for rec in self:
            rec.with_vouchers = bool(rec.voucher_ids)
            _logger.debug("Batch %s -> with_vouchers=%s", rec.display_name, rec.with_vouchers)

    def do_print_and_assign(self):
        _logger.info("🖨️ Ejecutando do_print_and_assign() para batch %s", self.display_name)
        if not self.book_id:
            raise UserError("Primero debe setear un talonario")
        if not self.book_id.autoprinted:
            _logger.info("📘 Talonario %s NO autoprinted → solo imprime sin asignar números.", self.book_id.display_name)
            self.printed = True
            return self.with_context(batch=True).do_print_batch_vouchers()
        _logger.info("📘 Talonario %s autoprinted → asignando números antes de imprimir.", self.book_id.display_name)
        self.assign_numbers(1, self.book_id)
        return self.do_print_batch_vouchers()

    def do_print_batch_vouchers(self):
        _logger.info("🖨️ Ejecutando do_print_batch_vouchers (QWeb) para batch %s", self.display_name)
        return self.env.ref("stock_batch_picking_voucher.batch_picking_preprinted_qweb").report_action(self)


    def do_clean(self):
        _logger.warning("🧹 Limpiando remitos del batch %s", self.display_name)
        self.voucher_ids.unlink()
        self.message_post(body=_("The assigned voucher were deleted"))
