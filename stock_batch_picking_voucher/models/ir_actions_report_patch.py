from odoo import models

class IrActionsReport(models.Model):
    _inherit = "ir.actions.report"

    def _get_report_type(self):
        res = super()._get_report_type()
        if ('aeroo', 'Aeroo Reports') not in res:
            res.append(('aeroo', 'Aeroo Reports'))
        return res
