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
  "name"                 :  "Odoo Marketplace Advertisement Manager",
  "summary"              :  """Sellers of marketplace can purchase an ad block and advertise their products.""",
  "category"             :  "website",
  "version"              :  "1.0.0",
  "sequence"             :  0,
  "author"               :  "Webkul Software Pvt. Ltd.",
  "license"              :  "Other proprietary",
  "website"              :  "https://store.webkul.com/Odoo-Marketplace-Advertisement-Manager.html",
  "description"          :  """https://webkul.com/blog/odoo-marketplace-advertisement-manager/""",
  "live_test_url"        :  "http://odoodemo.webkul.com/?module=marketplace_advertisement_manager&lifetime=120&lout=0&custom_url=/advertisement",
  "depends"              :  [
                             'odoo_marketplace',
                             'website_advertisement_manager',
                            ],
  "data"                 :  [
                             'security/access_control_security.xml',
                             'views/inherit_ad_block_views.xml',
                             'views/inherit_block_sol_views.xml',
                             'views/inherit_website_templates.xml',
                             'views/inherit_portal_account_ad_templates.xml',
                             'data/mp_ad_block_data.xml',
                            ],
  "assets"               :  {
        'web.assets_frontend':  [
          'marketplace_advertisement_manager/static/src/css/bootstrap-select.min.css',
          'marketplace_advertisement_manager/static/src/css/marketplace_ad.css',
          'marketplace_advertisement_manager/static/src/js/bootstrap-select.min.js',
          'marketplace_advertisement_manager/static/src/js/marketplace_ad.js'
        ]
  },
  "images"               :  ['static/description/Banner.gif'],
  "application"          :  True,
  "installable"          :  True,
  "auto_install"         :  False,
  "price"                :  99,
  "currency"             :  "USD",
  "pre_init_hook"        :  "pre_init_check",
}
