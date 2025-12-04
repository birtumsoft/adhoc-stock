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

        # 🔹 Log previo: datos crudos antes del super
        _logger.info("📥 Data recibida (RAW): %s", data)

        # 1️⃣ Decodificación inicial del JSON
        try:
            request_content = json.loads(data)
            report_action_url = request_content[0]
            report_type = request_content[1]
            _logger.info("🧾 ReportAction URL: %s", report_action_url)
            _logger.info("🧩 Tipo de reporte detectado (desde JSON): %s", report_type)
        except Exception as e:
            _logger.info("❌ Error parseando data JSON inicial: %s", e)
            return super().report_download(data, context=context, token=token, **kwargs)

        # 🔹 Antes de ejecutar el super, verificamos qué reporte apunta el nombre
        report_ref = None
        try:
            # Ejemplo de URL: "/report/pdf/stock_batch_picking_voucher.batch_picking_preprinted/123"
            parts = report_action_url.split('/')
            if len(parts) >= 4:
                report_ref = parts[3]
                _logger.info("🔎 Report_ref extraído: %s", report_ref)
                ir_report = request.env['ir.actions.report'].sudo().search([('report_name', '=', report_ref)], limit=1)
                if ir_report:
                    _logger.info(
                        "📘 Reporte encontrado en DB: id=%s | name=%s | tipo=%s | modelo=%s",
                        ir_report.id, ir_report.name, ir_report.report_type, ir_report.model,
                    )
                else:
                    _logger.info("⚠️ No se encontró ningún ir.actions.report con report_name='%s'", report_ref)
        except Exception as e:
            _logger.info("❌ Error analizando report_ref: %s", e)

        # 2️⃣ Ejecutamos el controlador original
        response = super().report_download(data, context=context, token=token, **kwargs)
        _logger.info("✅ Se ejecutó report_download original. Tipo recibido: %s", report_type)

        # 3️⃣ Si no es Aeroo, mostramos advertencia y salimos
        if report_type != "aeroo":
            _logger.info("⏩ Reporte NO Aeroo (%s). Odoo podría estar forzando QWeb.", report_type)
            if report_ref:
                # Confirmar desde DB el tipo actual, por si Odoo cambió el valor
                ir_report_db = request.env["ir.actions.report"].sudo().search(
                    [("report_name", "=", report_ref)], limit=1
                )
                if ir_report_db:
                    _logger.info(
                        "📊 Tipo real en base para '%s': %s", report_ref, ir_report_db.report_type
                    )
            return response

        # 4️⃣ Extraemos el contexto real que viajó
        try:
            json_string = json.loads(data)[0]
            if "context=" in json_string:
                context_part = json_string.split("context=")[1]
                decoded_context = urllib.parse.unquote(context_part)
                context_dict = json.loads(decoded_context)
                _logger.info("🧩 Contexto decodificado: %s", json.dumps(context_dict, indent=2))
                batch_id = context_dict.get("active_id")
                batch_flag = context_dict.get("batch")
                _logger.info("📦 batch_id=%s | batch=%s", batch_id, batch_flag)
            else:
                _logger.info("⚠️ No se encontró 'context=' en el string del reporte.")
                context_dict = {}
                batch_id = batch_flag = None
        except Exception as e:
            _logger.info("❌ Error extrayendo contexto del JSON: %s", e)
            return response

        # 5️⃣ Procesamos la asignación de remitos solo si aplica
        if batch_flag and batch_id and "batch_picking_preprinted" in data:
            batch = request.env["stock.picking.batch"].browse(batch_id)
            if not batch.exists():
                _logger.info("⚠️ No se encontró el batch con ID %s", batch_id)
                return response

            book_id = batch.book_id
            _logger.info("📘 Lote %s encontrado. Talonario: %s (autoprinted=%s)", batch.display_name, book_id.display_name, book_id.autoprinted)

            try:
                pdf_response = response.response[0]
                reader = PdfFileReader(io.BytesIO(pdf_response))
                number_pages = reader.getNumPages()
                _logger.info("📄 PDF con %s páginas detectadas.", number_pages)
            except Exception as e:
                _logger.info("❌ Error leyendo PDF: %s", e)
                return response

            if not batch.voucher_ids:
                _logger.info("🆕 Sin vouchers previos, asignando números automáticamente.")
                try:
                    batch.assign_numbers(number_pages, book_id)
                    _logger.info("✅ Asignación de remitos completada para batch %s.", batch_id)
                except Exception as e:
                    _logger.info("❌ Error asignando números: %s", e)
            else:
                _logger.info("ℹ️ El batch %s ya tiene vouchers asignados.", batch_id)

        else:
            _logger.info("⚠️ No se cumplen condiciones para asignar remitos automáticos. batch_flag=%s | batch_id=%s", batch_flag, batch_id)

        return response
