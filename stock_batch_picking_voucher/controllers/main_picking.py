import io
import json
import urllib.parse
import logging
from odoo.addons.web.controllers import report
from odoo.http import request, route
from PyPDF2 import PdfFileReader

_logger = logging.getLogger(__name__)


class ReportControllerPicking(report.ReportController):
    @route()
    def report_download(self, data, context=None, token=None, **kwargs):
        """Intercepta la descarga de reportes Aeroo para stock.picking."""
        _logger.info("➡️ Entrando en report_download (custom stock.picking Aeroo preimpreso)")

        _logger.info("📥 Data recibida (RAW): %s", data)

        # 1️⃣ Parsear contenido del request
        try:
            request_content = json.loads(data)
            report_action_url = request_content[0]
            report_type = request_content[1]
            _logger.info("🧾 ReportAction URL: %s", report_action_url)
            _logger.info("🧩 Tipo de reporte detectado (desde JSON): %s", report_type)
        except Exception as e:
            _logger.info("❌ Error parseando data JSON: %s", e)
            return super().report_download(data, context=context, token=token, **kwargs)

        # 2️⃣ Buscar el reporte que se está generando
        report_ref = None
        try:
            parts = report_action_url.split('/')
            if len(parts) >= 4:
                report_ref = parts[3]
                _logger.info("🔎 Report_ref extraído: %s", report_ref)
                ir_report = request.env['ir.actions.report'].sudo().search([('report_name', '=', report_ref)], limit=1)
                if ir_report:
                    _logger.info("📘 Reporte encontrado en DB: id=%s | name=%s | tipo=%s | modelo=%s",
                                 ir_report.id, ir_report.name, ir_report.report_type, ir_report.model)
        except Exception as e:
            _logger.info("❌ Error analizando report_ref: %s", e)

        # 3️⃣ Ejecutar el super y obtener respuesta original
        response = super().report_download(data, context=context, token=token, **kwargs)
        _logger.info("✅ Se ejecutó report_download original. Tipo recibido: %s", report_type)

        # 4️⃣ Solo intervenir si es Aeroo y el modelo es stock.picking
        if report_type != "aeroo" or not ir_report or ir_report.model != "stock.picking":
            _logger.info("⏩ Reporte no Aeroo o modelo distinto de stock.picking. Salimos sin intervención.")
            return response

        # 5️⃣ Decodificar contexto
        try:
            json_string = json.loads(data)[0]
            if "context=" in json_string:
                context_part = json_string.split("context=")[1]
                decoded_context = urllib.parse.unquote(context_part)
                context_dict = json.loads(decoded_context)
                _logger.info("🧩 Contexto decodificado: %s", json.dumps(context_dict, indent=2))
                picking_id = context_dict.get("active_id")
            else:
                _logger.info("⚠️ No se encontró 'context=' en el string del reporte.")
                picking_id = None
        except Exception as e:
            _logger.info("❌ Error extrayendo contexto del JSON: %s", e)
            return response

        # 6️⃣ Procesar la asignación (opcional)
        if picking_id:
            picking = request.env["stock.picking"].browse(picking_id)
            if picking.exists():
                _logger.info("📦 Picking encontrado: %s", picking.display_name)
                book = picking.book_id
                if book and book.autoprinted:
                    _logger.info("📘 Talonario '%s' es autoprinted → asigna número automáticamente.", book.display_name)
                    try:
                        pdf_response = response.response[0]
                        reader = PdfFileReader(io.BytesIO(pdf_response))
                        number_pages = reader.getNumPages()
                        _logger.info("📄 PDF con %s páginas detectadas.", number_pages)
                        picking.assign_numbers(number_pages, book)
                        _logger.info("✅ Números asignados correctamente para picking %s", picking.name)
                    except Exception as e:
                        _logger.info("❌ Error asignando números: %s", e)
            else:
                _logger.info("⚠️ No se encontró picking con ID %s", picking_id)

        return response
