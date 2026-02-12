

import logging
import json
from datetime import datetime, date
from werkzeug.exceptions import NotFound

from odoo import http,fields,tools
from odoo.http import request
from odoo.addons.http_routing.models.ir_http import slug
from odoo.addons.website_sale.controllers.main import TableCompute, QueryURL, WebsiteSale
from odoo.addons.payment import utils as payment_utils
from odoo.tools.misc import flatten
from odoo.tools.json import scriptsafe as json_scriptsafe
from odoo.tools import lazy

_logger = logging.getLogger(__name__)

try:
    import urlparse
    from urllib import urlencode
except: # For Python 3
    import urllib.parse as urlparse
    from urllib.parse import urlencode

class WebsiteRentalSale(http.Controller):

    @http.route(["/set/tenure/maxvalue"], type="json", auth="public", website=True)
    def _set_tenure_maxvalue(self, product_id, tenure_uom_id):
        product_id = request.env['product.product'].sudo().browse(product_id)
        max_tenure_value = product_id.get_tenure_maxvalue(int(tenure_uom_id))
        return {"max_value": max_tenure_value,}

    @http.route(["/get/tenure/price"], type="json", auth="public", website=True)
    def _get_tenure_price(self, product_id, tenure_uom_id=None, tenure_value=None, tenure_id=None):
        if tenure_id:
            rent_price = request.env['product.rental.tenure'].browse(int(tenure_id)).rent_price
            rent_price = request.env["website"].get_website_price(request.env['product.product'].sudo().browse(product_id),rent_price)
            return str('%.2f' % rent_price)
        tenure_uom_id = request.env['uom.uom'].sudo().browse(tenure_uom_id).id or False
        product_id = request.env['product.product'].sudo().browse(product_id)
        max_tenure_value = product_id.get_tenure_maxvalue(int(tenure_uom_id))
        if float(tenure_value) > max_tenure_value:
            return {"error": "true", "max_value": request.env["website"].get_website_price(product_id,max_tenure_value),}

        if tenure_uom_id and tenure_value and product_id:
            tenure_price = product_id.get_product_tenure_price(float(tenure_value), tenure_uom_id)
            return {"error": "false","tenure_price":str('%.2f' % round(request.env["website"].get_website_price(product_id,tenure_price[1]), 2)),} if tenure_price else {}

    @http.route(['/rental/order/renew'], type='http', auth='public', website=True,)
    def renew_rental_order(self, **kw):
        url = request.httprequest.referrer
        params = {}
        try:
            product_id = request.env['product.product'].browse(int(kw.get('product_id')))
            rental_order = kw.get('is_rental_product', None) and product_id.rental_ok
            sale_order_line_id = request.env['sale.order.line'].browse(int(kw.get("sale_order_line_id")))
            if rental_order:
                tenure_uom = False
                tenure_value = 0
                tenure_price = 0
                if kw.get('standard') and kw.get('tenure_id'):
                    tenure_id = request.env['product.rental.tenure'].browse(int(kw.get('tenure_id')) if kw.get('tenure_id') else False)
                    tenure_uom = tenure_id.rental_uom_id.id if tenure_id else False
                    tenure_value = float(tenure_id.tenure_value) if tenure_id else 0
                    tenure_price = float(tenure_id.rent_price) if tenure_id else 0

                if kw.get('custom') and kw.get('custom_tenure_price'):
                    tenure_uom = request.env['uom.uom'].sudo().browse(kw.get('tenure_uom')).id or False
                    tenure_value = float(kw.get('tenure_value')) or 0
                    tenure_price = float(product_id.get_product_tenure_price(tenure_value, tenure_uom) or kw.get('custom_tenure_price') or 0)

                    return_value_price_pair = product_id.get_product_tenure_price(tenure_value, tenure_uom)
                    if return_value_price_pair:
                        tenure_value = return_value_price_pair[0]
                        tenure_price = return_value_price_pair[1]
                taxes_ids = []

                if product_id.sudo().taxes_id:
                    taxes_ids = product_id.taxes_id.ids
                ro_contract_values = {
                    'sale_order_line_id': sale_order_line_id.id,
                    'product_rental_agreement_id': product_id.rental_agreement_id.id,
                    'price_unit': sale_order_line_id.product_id.currency_id.compute(tenure_price, sale_order_line_id.order_id.pricelist_id.currency_id),
                    'rental_qty': sale_order_line_id.product_uom_qty,
                    'rental_uom_id': tenure_uom,
                    'rental_tenure': tenure_value,
                    'tax_ids': [(6, 0, taxes_ids)],
                    'is_renewal_contract': True,
                }

                new_created_rental_contract = request.env['rental.order.contract'].sudo().create(ro_contract_values)
                new_created_rental_contract.action_confirm()
                new_created_rental_contract = new_created_rental_contract.sudo()
                inv = new_created_rental_contract.create_rental_invoice()
                inv_id = inv.get("res_id") or False
                if inv_id:

                    inv_obj = request.env['account.move'].browse(int(inv_id))
                    inv_obj.sudo().action_post()
                    params = {'renew_success': inv_obj.id}

                if new_created_rental_contract and len(sale_order_line_id.rental_contract_ids) == 1:
                    sale_order_line_id.sudo().inital_rental_contract_id = new_created_rental_contract.id

                else:

                    contract_to_check = False
                    if sale_order_line_id.sudo().current_rental_contract_id:
                        contract_to_check = sale_order_line_id.sudo().current_rental_contract_id
                    else:
                        contract_to_check = sale_order_line_id.sudo().inital_rental_contract_id
                    if contract_to_check and not (contract_to_check.check_product_received()):
                        #code to link current contract done move to latest contrcat
                        new_created_rental_contract.link_move_to_new_contract(
                            contract_to_check, new_created_rental_contract)
                        new_created_rental_contract.start_time = fields.datetime.now()
                        sale_order_line_id.sudo().current_start_time = new_created_rental_contract.start_time

                    sale_order_line_id.sudo().write({
                        "current_rental_contract_id": new_created_rental_contract.id,
                        "last_renewal_time": datetime.now(),
                    })

                    new_created_rental_contract.sale_order_line_id.sudo().write(
                        {"rental_state": "in_progress"})


        except Exception as e:

            params = {'renew_error': 1}
            pass
        url_parts = list(urlparse.urlparse(url))
        query = dict(urlparse.parse_qsl(url_parts[4]))
        if query.get("renew_success") or query.get("renew_error"):
            pass
        else:
            query.update(params)
        url_parts[4] = urlencode(query)
        url = urlparse.urlunparse(url_parts)
        return request.redirect(url)

class WebsiteSale(WebsiteSale):

    def _get_search_options(
        self, category=None, attrib_values=None, tags=None, min_price=0.0, max_price=0.0, conversion_rate=1, **post
    ):
        res = super()._get_search_options(category, attrib_values, tags, min_price, max_price, conversion_rate, **post)
        res.update({
            'rental': post.get('rental'),
        })
        return res

    def _shop_get_query_url_kwargs(self, category, search, min_price, max_price, attrib=None, order=None, **post):
        res = super()._shop_get_query_url_kwargs(category, search, min_price, max_price, attrib, order, **post)
        res.update({
            'rental': post.get('rental'),
        })
        return res

    @http.route([
        '/rental',
        '/rental/page/<int:page>',
        '/rental/category/<model("product.public.category"):category>',
        '/rental/category/<model("product.public.category"):category>/page/<int:page>',
    ], type='http', auth="public", website=True)
    def shop_rental(self, page=0, category=None, search='', min_price=0.0, max_price=0.0, ppg=False, **post):
        post['rental']= True
        res = super().shop(page, category, search, min_price, max_price, ppg, **post)
        category = res.qcontext.get('category')
        keep = QueryURL('/rental', **self._shop_get_query_url_kwargs(category and int(category), search, min_price, max_price, **post))
        

        website = request.env['website'].get_current_website()
        url = "/rental"
        if category:
            url = "/rental/category/%s" % slug(category)
        product_count = res.qcontext.get('search_count')
        ppg = res.qcontext.get('ppg')
        pager = website.pager(url=url, total=product_count, page=page, step=ppg, scope=7, url_args=post)

        res.qcontext.update({
            'keep': keep,
            'pager': pager,
            'rental': True,
        })
        return res

    @http.route(['/shop/<model("product.template"):product>'], type='http', auth="public", website=True)
    def product(self, product, category='', search='', **kwargs):
        res = super(WebsiteSale, self).product(product, category, search, **kwargs)
        attrib_list = request.httprequest.args.getlist('attrib')
        keep = QueryURL('/rental', category=category, search=search, attrib=attrib_list)
        is_rental = kwargs.get('rental',False)

        rental_tenure_lines = product.rental_tenure_ids

        price = {}
        for prod in rental_tenure_lines:
            if prod.is_default:
                duration = prod.rental_uom_id.duration_unit
                r_price = prod.rent_price
                tenure = prod.tenure_value
                if duration == 'hours':
                    result = r_price/(60*tenure)
                elif duration == 'days':
                    result = r_price/(60*24*tenure)
                elif duration == 'weeks':
                    result = r_price/(60*24*7*tenure)
                elif duration == 'months':
                    result = r_price/(60*24*7*30*tenure)
                elif duration == 'years':
                    result = r_price/(60*24*7*30*365*tenure)
                elif duration == 'minutes':
                    result = r_price/(tenure)
                
                result= f'{result:.10f}'
                price[float(result)] = prod

        min_val = min(price) if price else False

        res.qcontext.update({
            'keep' : keep,
            'rental':is_rental,
            'is_rental_product' : True,
            'min_tenure_price' : price[min_val].rent_price if price else 0,
            'min_rental_unit' : price[min_val].rental_uom_id.duration_unit if price else 0,
        })
        return res

    @http.route()
    def cart_update(self, product_id, add_qty=1, set_qty=0, **kw):

        product_id = request.env['product.product'].browse(int(product_id))
        rental_order = kw.get('is_rental_product', None) and product_id.rental_ok
        if rental_order:
            try:
                tenure_uom = False
                tenure_value = 0
                tenure_price = 0
                if not kw.get('standard') and not kw.get('custom'):
                    return request.redirect("/shop/cart")
                if kw.get('standard') and kw.get('tenure_id'):
                    tenure_id = request.env['product.rental.tenure'].browse(int(kw.get('tenure_id')) if kw.get('tenure_id') else False)
                    tenure_uom = tenure_id.rental_uom_id.id if tenure_id else False
                    tenure_value = float(tenure_id.tenure_value) if tenure_id else 0
                    tenure_price = float(tenure_id.rent_price) if tenure_id else 0
                    tenure_price = request.env["website"].get_website_price(product_id,tenure_price)

                if kw.get('custom') and kw.get('custom_tenure_price') :
                    tenure_uom = request.env['uom.uom'].sudo().browse(kw.get('tenure_uom')).id or False
                    tenure_value = float(kw.get('tenure_value')) or 0
                    tenure_price = float(product_id.get_product_tenure_price(tenure_value, tenure_uom)[1] or kw.get('custom_tenure_price') or 0)
                    return_value_price_pair = product_id.get_product_tenure_price(tenure_value, tenure_uom)
                    if return_value_price_pair:
                        tenure_value = return_value_price_pair[0]
                        tenure_price = return_value_price_pair[1]
                so = request.website.sale_get_order(force_create=1)
                if so.state != 'draft':
                    request.session['sale_order_id'] = None
                    so = request.website.sale_get_order(force_create=True)
                rental_vals = {
                    'tenure_uom' : tenure_uom,
                    'tenure_value' : tenure_value,
                    'tenure_price' : tenure_price,
                }
                product_custom_attribute_values = None
                if kw.get('product_custom_attribute_values'):
                    product_custom_attribute_values = json.loads(kw.get('product_custom_attribute_values'))
                no_variant_attribute_values = None
                if kw.get('no_variant_attribute_values'):
                    no_variant_attribute_values = json.loads(kw.get('no_variant_attribute_values'))
                line = so.with_context(rental_vals=rental_vals)._cart_update(
                    product_id=int(product_id),
                    add_qty=float(add_qty),
                    set_qty=float(set_qty),
                    product_custom_attribute_values=product_custom_attribute_values,
                    no_variant_attribute_values=no_variant_attribute_values,
                    rental_order = True,
                    tenure_uom = tenure_uom,
                    tenure_value = tenure_value,
                )
                return request.redirect("/shop/cart")
            except:
                return request.redirect("/shop/cart")
        res = super(WebsiteSale, self).cart_update(product_id, add_qty, set_qty, **kw)
        return res

    @http.route(['/shop/cart/update_json'], type='json', auth="public", methods=['POST'], website=True, csrf=False)
    def cart_update_json(self, product_id, line_id=None, add_qty=None, set_qty=None, display=True,product_custom_attribute_values=None, no_variant_attribute_values=None, **kw):
        """
        This route is called :
            - When changing quantity from the cart.
            - When adding a product from the wishlist.
            - When adding a product to cart on the same page (without redirection).
        """

        product_id = request.env['product.product'].browse(int(product_id))

        rental_order = kw.get('is_rental_product', None) and product_id.rental_ok
        if rental_order:
            try:
                tenure_uom = False
                tenure_value = 0
                tenure_price = 0
                if not kw.get('standard') and not kw.get('custom'):
                    return request.redirect("/shop/cart")
                if kw.get('standard') and kw.get('tenure_id'):
                    tenure_id = request.env['product.rental.tenure'].browse(int(kw.get('tenure_id')) if kw.get('tenure_id') else False)
                    tenure_uom = tenure_id.rental_uom_id.id if tenure_id else False
                    tenure_value = float(tenure_id.tenure_value) if tenure_id else 0
                    tenure_price = float(tenure_id.rent_price) if tenure_id else 0
                    tenure_price = request.env["website"].get_website_price(product_id,tenure_price)

                if kw.get('custom') and kw.get('custom_tenure_price') :
                    tenure_uom = request.env['uom.uom'].sudo().browse(int(kw.get('tenure_uom'))).id or False
                    tenure_value = float(kw.get('tenure_value')) or 0
                    tenure_price = float(product_id.get_product_tenure_price(tenure_value, tenure_uom)[1] or kw.get('custom_tenure_price') or 0)
                    return_value_price_pair = product_id.get_product_tenure_price(tenure_value, tenure_uom)
                    if return_value_price_pair:
                        tenure_value = return_value_price_pair[0]
                        tenure_price = return_value_price_pair[1]
                so = request.website.sale_get_order(force_create=1)
                if so.state != 'draft':
                    request.session['sale_order_id'] = None
                    so = request.website.sale_get_order(force_create=True)

                order = request.website.sale_get_order(force_create=True)
                if order.state != 'draft':
                    request.website.sale_reset()
                    if kw.get('force_create'):
                        order = request.website.sale_get_order(force_create=True)
                    else:
                        return {}

                rental_vals = {
                    'tenure_uom' : tenure_uom,
                    'tenure_value' : tenure_value,
                    'tenure_price' : tenure_price,
                }
                if product_custom_attribute_values:
                    product_custom_attribute_values = json_scriptsafe.loads(product_custom_attribute_values)

                if no_variant_attribute_values:
                    no_variant_attribute_values = json_scriptsafe.loads(no_variant_attribute_values)
                value = order.with_context(rental_vals=rental_vals)._cart_update(
                    product_id=product_id.id,
                    line_id=line_id,
                    add_qty=add_qty,
                    set_qty=set_qty,
                    product_custom_attribute_values=product_custom_attribute_values,
                    no_variant_attribute_values=no_variant_attribute_values,
                    rental_order = True,
                    tenure_uom = tenure_uom,
                    tenure_value = tenure_value,
                )

                if not order.cart_quantity:
                    request.website.sale_reset()
                    return value

                order = request.website.sale_get_order()
                value['notification_info'] = self._get_cart_notification_information(order, [value['line_id']])
                value['cart_quantity'] = order.cart_quantity
                value['minor_amount'] = payment_utils.to_minor_currency_units(
                    order.amount_total, order.currency_id
                ),
                value['amount'] = order.amount_total

                if not display:
                    return value
                
                value['cart_ready'] = order._is_cart_ready()

                value['website_sale.cart_lines'] = request.env['ir.ui.view']._render_template("website_sale.cart_lines", {
                    'website_sale_order': order,
                    'date': fields.Date.today(),
                    'suggested_products': order._cart_accessories()
                })
                value['website_sale.total'] = request.env['ir.ui.view']._render_template(
                    "website_sale.total", {
                        'website_sale_order': order,
                    }
                )
                return value
            except:
                return super(WebsiteSale, self).cart_update_json(product_id.id, line_id, add_qty, set_qty, display, product_custom_attribute_values, no_variant_attribute_values, **kw)
        else:
            res = super(WebsiteSale, self).cart_update_json(product_id.id, line_id, add_qty, set_qty, display, product_custom_attribute_values, no_variant_attribute_values, **kw)
            return res
