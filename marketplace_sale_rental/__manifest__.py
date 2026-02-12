# -*- coding: utf-8 -*-
#################################################################################
# Author      : Webkul Software Pvt. Ltd. (<https://webkul.com/>)
# Copyright(c): 2015-Present Webkul Software Pvt. Ltd.
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
{
  "name"                 :  "Odoo Marketplace Rental Sale",
  "summary"              :  """This module will enable rental feature in Odoo Marketplace.""",
  "category"             :  "website",
  "version"              :  "1.0.0",
  "sequence"             :  0,
  "author"               :  "Webkul Software Pvt. Ltd.",
  "license"              :  "Other proprietary",
  "website"              :  "https://store.webkul.com",
  "description"          :  """https://webkul.com/blog""",
  "live_test_url"        :  "http://odoodemo.webkul.com/?module=marketplace_sale_rental&lifetime=120&lout=0&custom_url=/shop/rental",
  "depends"              :  [
                             'odoo_marketplace',
                             'odoo_website_sale_rental',
                            ],
  "data"                 :  [
                             'security/access_control_security.xml',
                             'security/ir.model.access.csv',
                             'views/rental_views.xml',
                             'views/mp_rental_menu_view.xml',
                             'views/inherit_mp_dashboard.xml',
                             'data/mp_sale_rental_data.xml',
                            ],
  "images"               :  ['static/description/Banner.gif'],
  "application"          :  True,
  "installable"          :  True,
  "auto_install"         :  False,
  "price"                :  99,
  "currency"             :  "USD",
  "pre_init_hook"        :  "pre_init_check",
}