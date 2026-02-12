# -*- coding: utf-8 -*-
#################################################################################
# Author      : Webkul Software Pvt. Ltd. (<https://webkul.com/>)
# Copyright(c): 2015-Present Webkul Software Pvt. Ltd.
# License URL : https://store.webkul.com/license.html/
# All Rights Reserved.
#
#
#
# This program is copyright property of the author mentioned above.
# You can`t redistribute it and/or modify it.
#
#
# You should have received a copy of the License along with this program.
# If not, see <https://store.webkul.com/license.html/>
#################################################################################

from odoo import api, fields, models, _
import logging
_logger = logging.getLogger(__name__)
from odoo.exceptions import UserError

class RentalOrderContract(models.Model):
    _inherit = "rental.order.contract"

    marketplace_seller_id = fields.Many2one("res.partner",
        string="Seller",
        related = 'sale_order_line_id.marketplace_seller_id',
        store=True,
        )

    def view_outgoing_delivery_order(self):
        res = super(RentalOrderContract, self).view_outgoing_delivery_order()
        if self._context.get('mp_rental'):
            self.ensure_one()
            action = self.env.ref('odoo_marketplace.marketplace_stock_picking_action').read()[0]
            rental_out_picking_ids = self.stock_move_ids.filtered(
                lambda r: r.picking_type_id.code == "outgoing").mapped("picking_id")
            if len(rental_out_picking_ids) > 1:
                action['domain'] = [('id', 'in', rental_out_picking_ids.ids)]
            elif rental_out_picking_ids:
                action['views'] = [
                    (self.env.ref('odoo_marketplace.marketplace_picking_stock_modified_form_view').id, 'form')]
                action['res_id'] = rental_out_picking_ids.id
            else:
                action['domain'] = [('id', 'in', [])]
            return action
        return res

    def view_return_delivery_order(self):
        res = super(RentalOrderContract, self).view_return_delivery_order()
        if self._context.get('mp_rental'):
            self.ensure_one()
            action = self.env.ref('odoo_marketplace.marketplace_stock_picking_action').read()[0]
            rental_in_picking_ids = self.stock_move_ids.filtered(
                lambda r: r.picking_type_id.code == "incoming").mapped("picking_id")
            if len(rental_in_picking_ids) > 1:
                action['domain'] = [('id', 'in', rental_in_picking_ids.ids)]
            elif rental_in_picking_ids:
                action['views'] = [
                    (self.env.ref('odoo_marketplace.marketplace_picking_stock_modified_form_view').id, 'form')]
                action['res_id'] = rental_in_picking_ids.id
            else:
                action['domain'] = [('id', 'in', [])]
            return action
        return res

    def create_rental_invoice(self):
        res = super(RentalOrderContract, self).create_rental_invoice()
        for rec in self:
            inv_id = res and res['res_id']
            if inv_id:
                InvoiceObj = self.env['account.move']
                InvoiceObj.browse(inv_id).with_context(rental_contract=rec.name).create_seller_invoice_new()
        return res

class RentalProductAgreement(models.Model):
    _inherit = 'rental.product.agreement'

    @api.model
    def _set_seller_id(self):
        user_obj = self.env['res.users'].sudo().browse(self._uid)
        if user_obj.partner_id and user_obj.partner_id.seller:
            return user_obj.partner_id.id
        return self.env['res.partner']

    marketplace_seller_id = fields.Many2one("res.partner",
        string="Seller",
        default=_set_seller_id,
        copy=False,
        )

class SaleOrderLine(models.Model):
    _inherit = 'sale.order.line'

    def view_current_rental_order(self):
        current_rental_contract_id = self.rental_contract_ids.search([('sale_order_line_id','=',self.id)], limit=1, order="create_date desc")
        view_id = self.env.ref('marketplace_sale_rental.mp_rental_inherit_order_contract_view_form').id
        return {
            'name': 'Rental Contract',
            'view_type': 'form',
            'view_mode': 'form',
            'views': [(view_id, 'form')],
            'res_model': 'rental.order.contract',
            'res_id': current_rental_contract_id.id,
            'view_id': view_id,
            'type': 'ir.actions.act_window',
            'target': 'self',
        }

    def view_outgoing_delivery_order(self):
        res = super(SaleOrderLine, self).view_outgoing_delivery_order()
        if self._context.get('mp_rental'):
            self.ensure_one()
            action = self.env.ref('odoo_marketplace.marketplace_stock_picking_action').read()[0]
            rental_out_picking_ids = self.order_id.picking_ids.filtered(
                lambda r: r.picking_type_id.code == "outgoing" and r.move_ids.filtered(
                    lambda sm: sm.product_id == self.product_id))
            if len(rental_out_picking_ids) > 1:
                action['domain'] = [('id', 'in', rental_out_picking_ids.ids)]
            elif rental_out_picking_ids:
                action['views'] = [
                    (self.env.ref('odoo_marketplace.marketplace_picking_stock_modified_form_view').id, 'form')]
                action['res_id'] = rental_out_picking_ids.id
            else:
                action['domain'] = [('id', 'in', [])]
            return action
        return res

    def view_return_delivery_order(self):
        res = super(SaleOrderLine, self).view_return_delivery_order()
        if self._context.get('mp_rental'):
            self.ensure_one()
            action = self.env.ref('odoo_marketplace.marketplace_stock_picking_action').read()[0]
            rental_in_picking_ids = self.order_id.picking_ids.filtered(
                lambda r: r.picking_type_id.code == "incoming" and r.move_ids.product_id == self.product_id)
            if len(rental_in_picking_ids) > 1:
                action['domain'] = [('id', 'in', rental_in_picking_ids.ids)]
            elif rental_in_picking_ids:
                action['views'] = [
                    (self.env.ref('odoo_marketplace.marketplace_picking_stock_modified_form_view').id, 'form')]
                action['res_id'] = rental_in_picking_ids.id
            else:
                action['domain'] = [('id', 'in', [])]
            return action
        return res

    @api.depends('invoice_lines')
    def _compute_rental_invoice(self):
        for line in self.sudo():
            line.rental_invoice_count = 0
            if line.invoice_lines:
                invoice_lines = line.invoice_lines.filtered(
                    lambda r: r.product_id == line.product_id)
                invoice_ids = invoice_lines.filtered(
                    lambda r: r.move_id == line.order_id.invoice_ids)
                line.rental_invoice_count = len(
                    invoice_ids) if invoice_ids else 0


class ProductTemplate(models.Model):
    _inherit = "product.template"


    def toggle_website_published(self):
        for record in self:
            if record.rental_ok and not record.website_published and not record.tenure_type_standard and not record.tenure_type_custom:
                raise UserError(_("Please select tenure type standard/custom to publish this product."))
            if record.rental_ok and not record.website_published and not record.rental_tenure_ids:
                raise UserError(_("Please add atleast one Rental Tenure to publish this product."))
            if record.rental_ok and not record.website_published and not record.rental_tenure_id:
                raise UserError(_("Please select starting rental tenure to show in website."))
            record.sudo().website_published = not record.sudo().website_published
