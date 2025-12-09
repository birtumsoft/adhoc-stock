from odoo import api, models, SUPERUSER_ID


class ReportPaperformat(models.Model):
    _inherit = 'report.paperformat'

    @api.model
    def create_custom_a4_format(self):
        """Clona el formato A4 estándar y ajusta el margen superior."""
        paper_a4 = self.env['report.paperformat'].search([('name', '=', 'A4')], limit=1)
        if not paper_a4:
            return None

        # Verificar si ya existe nuestro formato
        custom_format = self.env['report.paperformat'].search([('name', '=', 'A4 Recibo de Entrega UX')], limit=1)
        if custom_format:
            return custom_format

        # Crear copia del A4 con nuevo margen superior
        new_format = paper_a4.copy({
            'name': 'A4 Recibo de Entrega UX',
            'margin_top': 48,
            'default': False,
        })

        # Registrar el nuevo formato con un XML-ID para poder usarlo desde XML
        self.env['ir.model.data'].create({
            'module': 'stock_voucher_ux',
            'name': 'paperformat_deliveryslip_a4',
            'model': 'report.paperformat',
            'res_id': new_format.id,
            'noupdate': True,
        })

        return new_format


def post_init_hook(cr, registry):
    """Hook que crea el nuevo formato al instalar/actualizar el módulo."""
    env = api.Environment(cr, SUPERUSER_ID, {})
    env['report.paperformat'].create_custom_a4_format()
