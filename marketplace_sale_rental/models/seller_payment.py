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


class account_invoice(models.Model):
    _inherit = 'account.move'

    @api.model
    def create_seller_payment_new(self, sellers_dict):
        rental_contract = self._context.get("rental_contract")
        memo = sellers_dict.get("memo")
        if rental_contract:
            sellers_dict.update({
                "memo": memo + "_" + rental_contract,
                "description": "Rental " + sellers_dict.get("description") + " corresponding to " + rental_contract,
            })
        res = super(account_invoice, self).create_seller_payment_new(sellers_dict)
        seller_payment_id = self.env['seller.payment'].search([], limit=1, order="create_date desc")
        if seller_payment_id:
            seller_payment_id.write({'memo': memo,})
        return res
