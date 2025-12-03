import io
import json
import urllib.parse
import logging

from odoo.addons.web.controllers import report
from odoo.http import request, route
from PyPDF2 import PdfFileReader

_logger = logging.getLogger(__name__)


class ReportController(report.ReportController):
    @route()
    def report_download(self, data, context=None, token=None, **kwargs):
        """Intercepta la descarga de reportes para contar páginas y asignar remitos."""
        _logger.info("➡️ Entrando en report_download (custom stock_batch_picking_voucher)")

        response = super().report_download(data, context=context, token=token, **kwargs)
        _logger.debug("✅ Se ejecutó report_download original. Data recibida: %s", data)

        try:
            requestcontent = json.loads(data)
            report_type = requestcontent[1]
            _logger.debug("Tipo de reporte detectado: %s", report_type)
        except Exception as e:
            _logger.error("❌ Error parseando data JSON: %s", e)
            return response

        # Solo actuar si es tipo aeroo
        if report_type != "aeroo":
            _logger.info("⏩ Reporte no Aeroo (%s), se devuelve sin intervención.", report_type)
            return response

        try:
            json_string = json.loads(data)[0]
            context_part = json_string.split("context=")[1]
            decoded_context = urllib.parse.unquote(context_part)
            context_dict = json.loads(decoded_context)
            batch_id = context_dict.get("active_id")
            batch_flag = context_dict.get("batch")
            _logger.info("📦 batch_id=%s | batch=%s", batch_id, batch_flag)
        except Exception as e:
            _logger.error("❌ Error extrayendo contexto: %s", e)
            return response

        if batch_flag and batch_id and "batch_picking_preprinted" in data:
            batch = request.env["stock.picking.batch"].browse(batch_id)
            book_id = batch.book_id
            _logger.info("📘 Lote %s encontrado. Talonario: %s", batch.display_name, book_id.display_name)

            try:
                pdf_response = response.response[0]
                reader = PdfFileReader(io.BytesIO(pdf_response))
                number_pages = reader.getNumPages()
                _logger.info("📄 PDF con %s páginas detectadas.", number_pages)
            except Exception as e:
                _logger.error("❌ Error leyendo PDF: %s", e)
                return response

            if not batch.voucher_ids:
                _logger.info("🆕 Sin vouchers previos, asignando números automáticamente.")
                try:
                    batch.assign_numbers(number_pages, book_id)
                    _logger.info("✅ Asignación de remitos completada para batch %s.", batch_id)
                except Exception as e:
                    _logger.error("❌ Error asignando números: %s", e)
            else:
                _logger.info("ℹ️ El batch %s ya tiene vouchers asignados.", batch_id)

        else:
            _logger.info("⚠️ No se cumplen condiciones para asignar remitos automáticos.")

        return response
