import logging
import os
from odoo import models, fields, api, _
from odoo.exceptions import UserError

_logger = logging.getLogger(__name__)

try:
    from pyafipws.cot import COT
except ImportError:
    COT = None


class ResCompany(models.Model):
    _inherit = "res.company"

    arba_cot = fields.Char(
        "Clave COT",
        help="Clave para generación de remito electrónico (ARBA COT).",
    )

    def get_arba_cot_login_url(self, environment_type):
        if environment_type == "production":
            return "https://cot.arba.gov.ar/TransporteBienes/SeguridadCliente/presentarRemitos.do"
        else:
            return "https://cot.test.arba.gov.ar/TransporteBienes/SeguridadCliente/presentarRemitos.do"

    def arba_cot_connect(self):
        self.ensure_one()
        if not COT:
            raise UserError(_("La librería pyafipws no está instalada."))

        cuit = self.partner_id.ensure_vat()
        if not self.arba_cot:
            raise UserError(_("Debe configurar la clave ARBA COT en la compañía %s.") % self.name)

        ws = COT()
        environment_type = self._get_environment_type()
        url = self.get_arba_cot_login_url(environment_type)
        _logger.info("Conectando a ARBA COT (%s) con CUIT %s", environment_type, cuit)
        ws.Usuario = cuit
        ws.Password = self.arba_cot
        ws.Conectar(url=url)
        return ws
