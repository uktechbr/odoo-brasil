# -*- coding: utf-8 -*-
# © 2016 Alessandro Fernandes Martini <alessandrofmartini@gmail.com>, Trustcode
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html)

import base64

from lxml import objectify
from dateutil import parser
from random import SystemRandom

from odoo import api, models, fields
from odoo.exceptions import UserError


class WizardImportNfe(models.TransientModel):
    _name = 'wizard.import.nfe'

    nfe_xml = fields.Binary(u'XML da NFe')
    fiscal_position_id = fields.Many2one('account.fiscal.position',
                                         string='Posição Fiscal')
    payment_term_id = fields.Many2one('account.payment.term',
                                      string='Forma de Pagamento')
    invoice_id = fields.Many2one('account.invoice', string='Fatura')
    serie = fields.Many2one('br_account.document.serie', string="Série")

    def get_identificacao(self, nfe):
        company = self.env['res.partner'].search([
            ('cnpj_cpf', '=', nfe.NFe.infNFe.emit)], limit=1)
        num_controle = int(''.join([str(SystemRandom().randrange(9))
                           for i in range(8)]))
        data_emissao = parser.parse(str(nfe.NFe.infNFe.ide.dhEmi))
        data_fatura = parser.parse(str(nfe.NFe.infNFe.ide.dhSaiEnt))
        ambiente = 'homologacao' if nfe.NFe.infNFe.ide.tpAmb == 2\
            else 'producao'
        finalidade_emissao = str(nfe.NFe.infNFe.ide.finNFe),
        numero_inv = self.env['invoice.eletronic'].search_count([])
        return dict(
            code='AUTO' + (self.invoice_id.number or ''),
            numero=numero_inv,
            company_id=company.id,
            name='Documento Eletrônico: nº ' + str(numero_inv),
            serie=self.serie.id,
            num_controle=num_controle,
            data_emissao=data_emissao,
            data_fatura=data_fatura,
            ambiente=ambiente,
            finalidade_emissao=finalidade_emissao
        )

    def get_total_values(self, nfe):
        total = nfe.NFe.infNFe.total.ICMSTot
        return dict(
            valor_final=total.vNF,
            valor_frete=total.vFrete,
            valor_seguro=total.vSeg,
            valor_bruto=total.vProd,
            valor_desconto=total.vDesc,
            valor_bc_icms=total.vBC,
            valor_icms=total.vICMS,
            valor_icms_deson=total.vICMSDeson,
            valor_icmsst=total.vST,
            valor_ii=total.vII,
            valor_ipi=total.vIPI,
            valor_pis=total.vPIS,
            valor_cofins=total.vCOFINS,
            valor_estimado_tributos=total.vTotTrib,
        )

    def get_main(self, nfe):
        ide = nfe.NFe.infNFe.ide
        dest = nfe.NFe.infNFe.dest
        partner_doc = dest.CNPJ if hasattr(dest, 'CNPJ') else dest.CPF
        partner = self.env['res.partner'].search([
            ('cnpj_cpf', '=', partner_doc)])

        return dict(
            model=str(ide.mod),
            invoice_id=self.invoice_id.id,
            partner_id=partner.id,
            tipo_operacao=str(ide.tpEmis),
            payment_term_id=self.payment_term_id.id,
            fiscal_position_id=self.fiscal_position_id,
        )

    def create_invoice_eletronic_item(self, item):
        product = self.env['product.product'].search([
            ('default_code', '=', item.prod.cProd)], limit=1)
        if not product:
            product = self.env['product.product'].search([
                ('barcode', '=', item.prod.cEAN)], limit=1)
        product_id = product.id
        uom_id = self.env['product.uom'].search([
            ('name', '=', item.prod.uCom)], limit=1).id
        quantidade = item.prod.qCom
        preco_unitario = item.prod.vUnCom
        valor_bruto = item.prod.vProd
        desconto = 0
        if hasattr(item.prod, 'vDesc'):
            desconto = item.prod.vDesc
        seguro = 0
        if hasattr(item.prod, 'vSeg'):
            seguro = item.prod.vSeg
        frete = 0
        if hasattr(item.prod, 'vFrete'):
            frete = item.prod.vFrete
        outras_despesas = 0
        if hasattr(item.prod, 'vOutro'):
            outras_despesas = item.prod.vOutro
        indicador_total = item.prod.indTot
        tipo_produto = product.fiscal_type
        cfop = item.prod.CFOP
        ncm = item.prod.NCM
        return self.env['invoice.eletronic.item'].create({
            'product_id': product_id, 'uom_id': uom_id,
            'quantidade': quantidade, 'preco_unitario': preco_unitario,
            'valor_bruto': valor_bruto, 'desconto': desconto, 'seguro': seguro,
            'frete': frete, 'outras_despesas': outras_despesas,
            'indicador_total': indicador_total, 'tipo_produto': tipo_produto,
            'cfop': cfop, 'ncm': ncm,
        })

    def get_items(self, nfe):
        items = []
        for det in nfe.NFe.infNFe.det:
            item = self.create_invoice_eletronic_item(det)
            items.append((4, item.id, False))
        return {'eletronic_item_ids': items}

    @api.multi
    def action_import_nfe(self):
        if not self.nfe_xml:
            raise UserError('Por favor, insira um arquivo de NFe.')
        nfe_string = base64.b64decode(self.nfe_xml)
        nfe = objectify.fromstring(nfe_string)

        invoice_dict = {}
        invoice_dict.update(self.get_main(nfe))
        invoice_dict.update(self.get_identificacao(nfe))
        invoice_dict.update(self.get_total_values(nfe))
        invoice_dict.update(self.get_items(nfe))
        self.env['invoice.eletronic'].create(invoice_dict)
