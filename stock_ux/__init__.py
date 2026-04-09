##############################################################################
# For copyright and license notices, see __manifest__.py file in module root
# directory
##############################################################################
from . import models
from . import wizards

def pre_init_hook(env):
    # PARCHE ODOO 19: Limpieza de Server Actions
    # Buscamos acciones que usen stock.move y tengan 'name': o "name":
    # Lo reemplazamos por 'description_picking': para evitar el crash del servidor
    env.cr.execute("""
        UPDATE ir_act_server 
        SET code = REPLACE(REPLACE(REPLACE(REPLACE(code, 
            '''name'':', '''description_picking'':'), 
            '"name":', '"description_picking":'),
            '''name'' :', '''description_picking'' :'),
            '"name" :', '"description_picking" :')
        WHERE code LIKE '%stock.move%'
    """)
