# -*- coding: utf-8 -*-
# © 2016 Alessandro Fernandes Martini <alessandrofmartini@gmail.com>, Trustcode
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html)

from odoo import fields, models


class InvoiceEletronicItem(models.Model):
    _inherit = 'invoice.eletronic.item'

    product_ean = fields.Char('EAN do Produto')
    product_cprod = fields.Char('Código Interno do Produto')
    product_xprod = fields.Char('Nome do produto')
