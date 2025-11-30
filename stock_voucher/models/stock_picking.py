import datetime
import logging
import re
import os
from odoo import models, fields, api, _
from odoo.exceptions import UserError

_logger = logging.getLogger(__name__)

try:
    from pyafipws.iibb import IIBB
except ImportError:
    IIBB = None


class StockPicking(models.Model):
    _inherit = "stock.picking"

    dispatch_number = fields.Char(
        help="Número de despacho vinculado a los lotes relacionados."
    )
    cot_numero_unico = fields.Char("COT - Nro Único")
    cot_numero_comprobante = fields.Char("COT - Nro Comprobante")
    cot = fields.Char("COT")

    def get_arba_file_data(
        self, datetime_out, tipo_recorrido, carrier_partner,
        patente_vehiculo, patente_acoplado, prod_no_term_dev, importe
    ):
        company = self.company_id
        if not company:
            raise UserError(_("El remito no tiene compañía asociada."))
        cuit = company.partner_id.ensure_vat()
        cuit_carrier = carrier_partner.ensure_vat()
        if cuit_carrier == cuit and not patente_vehiculo:
            raise UserError(_("Debe informar la patente del vehículo si la empresa es transportista."))

        nro_secuencial = self.env["ir.sequence"].with_company(company).next_by_code("arba.cot.file")
        if not nro_secuencial:
            raise UserError(_("No se encontró la secuencia 'arba.cot.file'."))

        filename = f"TB_{cuit}_000000_{datetime.date.today().strftime('%Y%m%d')}_{nro_secuencial}.txt"
        HEADER = ["01", cuit]
        FOOTER = ["04", "1"]

        CODIGO_DGI = "091"
        PREFIJO = "00001"
        NUMERO = re.sub(r"\D", "", self.l10n_ar_delivery_guide_number or "0").rjust(8, "0")

        REMITO = [
            "02",
            datetime.date.today().strftime("%Y%m%d"),
            f"{CODIGO_DGI}{PREFIJO}{NUMERO}",
            datetime_out.strftime("%Y%m%d"),
            datetime_out.strftime("%H%M"),
            "E",
            "0",
            "",
            "",
            cuit_carrier,
            carrier_partner.name[:50],
            "1",
            (carrier_partner.street or "")[:40],
            "",
            "S/N",
            "",
            "",
            "",
            (carrier_partner.zip or "")[:8],
            (carrier_partner.city or "")[:50],
            (carrier_partner.state_id.code or "")[:1],
            "",
            "NO",
            cuit,
            company.name[:50],
            "0",
            (company.street or "")[:40],
            "",
            "S/N",
            "",
            "",
            "",
            (company.zip or "")[:8],
            (company.city or "")[:50],
            (company.state_id.code or "")[:1],
            cuit_carrier,
            tipo_recorrido,
            "",
            "",
            "",
            patente_vehiculo or "",
            patente_acoplado or "",
            str(prod_no_term_dev),
            str(int(round(importe * 100.0)))[-14:],
        ]

        content = "\r".join(["|".join(HEADER), "|".join(REMITO), "|".join(FOOTER)])
        return content, filename

    def do_pyafipws_presentar_remito(
        self, datetime_out, tipo_recorrido, carrier_partner,
        patente_vehiculo, patente_acoplado, prod_no_term_dev, importe
    ):
        self.ensure_one()
        COT = self.company_id.arba_cot_connect()
        content, filename = self.get_arba_file_data(
            datetime_out, tipo_recorrido, carrier_partner,
            patente_vehiculo, patente_acoplado, prod_no_term_dev, importe
        )

        tmpfile = f"/tmp/{filename}"
        with open(tmpfile, "w") as f:
            f.write(content)
        _logger.info("Presentando remito COT con archivo %s", tmpfile)
        COT.PresentarRemito(tmpfile, testing="")
        os.remove(tmpfile)

        if COT.TipoError:
            raise UserError(f"Error al presentar remito: {COT.MensajeError}")
        self.write({
            "cot_numero_unico": COT.NumeroUnico,
            "cot_numero_comprobante": COT.NumeroComprobante,
            "cot": COT.COT,
        })
        self.message_post(
            body=_("Remito electrónico presentado con COT: %s") % COT.COT,
            subject=_("Remito COT presentado"),
            body_is_html=False,
        )
        return True
