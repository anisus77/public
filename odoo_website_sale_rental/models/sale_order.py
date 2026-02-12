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

from odoo import models,fields,api, _
from odoo.http import request
from collections import defaultdict
from odoo.tools.misc import formatLang
import logging
_logger = logging.getLogger(__name__)

class SaleOrder(models.Model):
    _inherit = "sale.order"

    def _prepare_order_line_values(
        self, product_id, quantity, linked_line_id=False,
        no_variant_attribute_values=None, product_custom_attribute_values=None,
        **kwargs
    ):
        res = super(SaleOrder, self)._prepare_order_line_values(product_id, quantity, linked_line_id,
        no_variant_attribute_values, product_custom_attribute_values,**kwargs)

        if self._context.get('rental_vals'):

            rental_vals = self._context.get('rental_vals')
            tenure_uom = int(rental_vals.get('tenure_uom')) if rental_vals.get('tenure_uom') else False
            tenure_value = float(rental_vals.get('tenure_value')) if rental_vals.get('tenure_value') else False
            tenure_price = float(rental_vals.get('tenure_price')) if rental_vals.get('tenure_price') else False
            product = self.env['product.product'].browse(product_id)
            security_amount = self.env["website"].get_website_price(product,product.security_amount)
            if product and product.rental_ok and tenure_uom:
                vals = {
                    'is_rental_order': True,
                    'price_unit': tenure_price,
                    'rental_uom_id': tenure_uom,
                    'rental_tenure': tenure_value,
                    'unit_security_amount': security_amount,
                }
                res.update(vals)
        return res

    def _prepare_order_line_update_values(
        self, order_line, quantity, linked_line_id=False, **kwargs
    ):
        res = super(SaleOrder, self)._prepare_order_line_update_values(order_line, quantity, linked_line_id, **kwargs)

        if order_line.product_id.rental_ok:
            price_unit = order_line.price_unit
            res.update({
                'price_unit' : price_unit,
                })
        return res

    def _cart_find_product_line(self, product_id=None, line_id=None, **kwargs):
        # check if new line needs to be created forcefully or not

        rental_order = kwargs.get('rental_order')
        tenure_uom = int(kwargs.get('tenure_uom')) if kwargs.get('tenure_uom') else False
        tenure_value = float(kwargs.get('tenure_value')) if kwargs.get('tenure_value') else False

        if not line_id:
            flag =0
            domain = [('order_id', '=', self.id), ('product_id', '=', product_id)]
            sol_obj = self.env['sale.order.line'].sudo().search(domain)
            if sol_obj:

                for sol in sol_obj:
                    if sol.is_rental_order and rental_order:
                        if sol.rental_tenure == tenure_value and sol.rental_uom_id.id == tenure_uom:
                            return self.env['sale.order.line'].sudo().browse(sol.id)
                        else:
                            flag = 1
                    if sol.is_rental_order and not rental_order:
                        flag = 1
                    if not sol.is_rental_order and rental_order:
                        flag = 1
                    if not sol.is_rental_order and not rental_order:
                        return self.env['sale.order.line'].sudo().browse(sol.id)

            if flag==1:
                return self.env['sale.order.line']

        self.ensure_one()
        product = self.env['product.product'].browse(product_id)

        # split lines with the same product if it has untracked attributes
        if product and product.mapped('attribute_line_ids').filtered(lambda r: not r.attribute_id.create_variant) and not line_id:
            return self.env['sale.order.line']

        domain = [('order_id', '=', self.id), ('product_id', '=', product_id)]
        if line_id:
            domain += [('id', '=', line_id)]
        return self.env['sale.order.line'].sudo().search(domain)


class SaleOrderLine(models.Model):
    _inherit = 'sale.order.line'

    def _get_display_price(self):
        res = super(SaleOrderLine, self)._get_display_price()
        if self._context.get("rental_vals"):
            price_unit = float(self._context.get("rental_vals").get("tenure_price"))
            return price_unit
        elif self.is_rental_order:
            price_unit = self.price_unit
            return price_unit
        return res


class RentalOrderContract(models.Model):
    _inherit = "rental.order.contract"

    rental_qty = fields.Float(
        "Quantity",
        readonly=True,
        tracking=True,
        related='sale_order_line_id.product_uom_qty',
    )

class AccountTax(models.Model):
    _inherit = 'account.tax'

    @api.model
    def _prepare_tax_totals(self, base_lines, currency, tax_lines=None, is_company_currency_requested=False):
        record = base_lines[0].get('record', False)
        if record and (record._name != 'sale.order.line'):
            return super(AccountTax,self)._prepare_tax_totals(base_lines, currency, tax_lines, is_company_currency_requested)
        
        to_process = []
        for base_line in base_lines:
            to_update_vals, tax_values_list = self._compute_taxes_for_single_line(base_line)
            to_process.append((base_line, to_update_vals, tax_values_list))

        def grouping_key_generator(base_line, tax_values):
            source_tax = tax_values['tax_repartition_line'].tax_id
            return {'tax_group': source_tax.tax_group_id}

        global_tax_details = self._aggregate_taxes(to_process, grouping_key_generator=grouping_key_generator)

        tax_group_vals_list = []
        for tax_detail in global_tax_details['tax_details'].values():
            tax_group_vals = {
                'tax_group': tax_detail['tax_group'],
                'base_amount': tax_detail['base_amount_currency'],
                'tax_amount': tax_detail['tax_amount_currency'],
            }

            # Handle a manual edition of tax lines.
            if tax_lines is not None:
                matched_tax_lines = [
                    x
                    for x in tax_lines
                    if (x['group_tax'] or x['tax_repartition_line'].tax_id).tax_group_id == tax_detail['tax_group']
                ]
                if matched_tax_lines:
                    tax_group_vals['tax_amount'] = sum(x['tax_amount'] for x in matched_tax_lines)

            tax_group_vals_list.append(tax_group_vals)

        tax_group_vals_list = sorted(tax_group_vals_list, key=lambda x: (x['tax_group'].sequence, x['tax_group'].id))

        # ==== Partition the tax group values by subtotals ====
        amt = sum([b.get('price_subtotal') for b in base_lines if b.get('price_subtotal')])
        amount_untaxed = amt
        amount_tax = 0.0

        subtotal_order = {}
        groups_by_subtotal = defaultdict(list)
        for tax_group_vals in tax_group_vals_list:
            tax_group = tax_group_vals['tax_group']

            subtotal_title = tax_group.preceding_subtotal or _("Untaxed Amount")
            sequence = tax_group.sequence

            subtotal_order[subtotal_title] = min(subtotal_order.get(subtotal_title, float('inf')), sequence)
            groups_by_subtotal[subtotal_title].append({
                'group_key': tax_group.id,
                'tax_group_id': tax_group.id,
                'tax_group_name': tax_group.name,
                'tax_group_amount': tax_group_vals['tax_amount'],
                'tax_group_base_amount': tax_group_vals['base_amount'],
                'formatted_tax_group_amount': formatLang(self.env, tax_group_vals['tax_amount'], currency_obj=currency),
                'formatted_tax_group_base_amount': formatLang(self.env, tax_group_vals['base_amount'], currency_obj=currency),
            })

        # ==== Build the final result ====

        subtotals = []
        for subtotal_title in sorted(subtotal_order.keys(), key=lambda k: subtotal_order[k]):
            amount_total = amount_untaxed + amount_tax
            subtotals.append({
                'name': subtotal_title,
                'amount': amount_total,
                'formatted_amount': formatLang(self.env, amount_total, currency_obj=currency),
            })
            amount_tax += sum(x['tax_group_amount'] for x in groups_by_subtotal[subtotal_title])

        amount_total = amount_untaxed + amount_tax

        display_tax_base = (len(global_tax_details['tax_details']) == 1 and currency.compare_amounts(tax_group_vals_list[0]['base_amount'], amount_untaxed) != 0)\
                        or len(global_tax_details['tax_details']) > 1

        return {
            'amount_untaxed': currency.round(amount_untaxed) if currency else amount_untaxed,
            'amount_total': currency.round(amount_total) if currency else amount_total,
            'formatted_amount_total': formatLang(self.env, amount_total, currency_obj=currency),
            'formatted_amount_untaxed': formatLang(self.env, amount_untaxed, currency_obj=currency),
            'groups_by_subtotal': groups_by_subtotal,
            'subtotals': subtotals,
            'subtotals_order': sorted(subtotal_order.keys(), key=lambda k: subtotal_order[k]),
            'display_tax_base': display_tax_base
        }
