import logging
from odoo import _, api, fields, models
from odoo.exceptions import UserError

_logger = logging.getLogger(__name__)


class StockPicking(models.Model):
    _inherit = "stock.picking"

    # --- NUEVOS CAMPOS HEREDADOS DEL BATCH ---
    voucher_ids = fields.One2many(
        "stock.picking.voucher",
        "picking_id",
        string="Remitos",
        copy=False,
    )

    book_id = fields.Many2one(
        "stock.book",
        string="Talonario",
        copy=False,
        ondelete="restrict",
        check_company=True,
    )

    next_number = fields.Integer(related="book_id.next_number")
    printed = fields.Boolean()

    with_vouchers = fields.Boolean(
        compute="_compute_with_vouchers",
        string="Con remitos asignados",
    )

    # --- CÁLCULO DE REMITOS EXISTENTES ---
    @api.depends("voucher_ids")
    def _compute_with_vouchers(self):
        for rec in self:
            rec.with_vouchers = bool(rec.voucher_ids)
            _logger.debug("Picking %s → with_vouchers=%s", rec.display_name, rec.with_vouchers)

    # --- NUEVO: ASIGNAR NÚMEROS DE REMITO ---
    def assign_numbers(self, estimated_number_of_pages, book):
        _logger.info("🧾 Asignando %s remitos para picking %s usando talonario %s",
                     estimated_number_of_pages, self.display_name, book.display_name)
        self.ensure_one()

        list_of_vouchers = []
        for page in range(estimated_number_of_pages):
            next_num = book.sequence_id.next_by_id()
            _logger.info("➡️ Generando número de remito: %s", next_num)
            list_of_vouchers.append({
                "name": next_num,
                "book_id": book.id,
                "picking_id": self.id,
            })

        self.env["stock.picking.voucher"].sudo().create(list_of_vouchers)
        self.message_post(body=_("Números de remitos asignados: %s") % (self.voucher_ids.mapped("display_name")))
        self.write({"book_id": book.id})
        _logger.info("✅ Remitos creados correctamente para picking %s", self.id)

    # --- IMPRESIÓN CON O SIN NUMERACIÓN ---
    def do_print_and_assign(self):
        _logger.info("🖨️ Ejecutando do_print_and_assign() para picking %s", self.display_name)

        self.ensure_one()

        if not self.book_id and self.picking_type_code != "incoming":
            raise UserError(_("Primero debe seleccionar un talonario"))

        if not self.book_id.autoprinted:
            _logger.info("📘 Talonario %s NO autoprinted → imprime reporte preimpreso Aeroo sin asignar números.",
                         self.book_id.display_name)
            self.printed = True
            return self.with_context(single=True).do_print_batch_vouchers()

        _logger.info("📘 Talonario %s autoprinted → asignando números antes de imprimir.",
                     self.book_id.display_name)
        self.assign_numbers(1, self.book_id)
        return self.do_print_batch_vouchers()

    # --- IMPRESIÓN AEROO (reporte preimpreso) ---
    def do_print_batch_vouchers(self):
        _logger.info("🖨️ Ejecutando do_print_batch_vouchers() para picking %s", self.display_name)
        try:
            action = self.env.ref("stock_batch_picking_voucher.batch_picking_preprinted").report_action(self)
            _logger.info("✅ Reporte Aeroo preimpreso ejecutado correctamente para picking %s", self.name)
            return action
        except Exception as e:
            _logger.error("❌ Error ejecutando reporte preimpreso Aeroo: %s", e)
            raise UserError(_("No se pudo generar el reporte preimpreso Aeroo."))

    # --- LIMPIEZA DE REMITOS ---
    def do_clean(self):
        _logger.warning("🧹 Limpiando remitos del picking %s", self.display_name)
        self.voucher_ids.unlink()
        self.message_post(body=_("Los remitos asignados fueron eliminados."))
