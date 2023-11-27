##############################################################################
#
#    Author: Oy Tawasta OS Technologies Ltd.
#    Copyright 2023 Oy Tawasta OS Technologies Ltd. (https://tawasta.fi)
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU Affero General Public License as
#    published by the Free Software Foundation, either version 3 of the
#    License, or (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
#    GNU Affero General Public License for more details.
#
#    You should have received a copy of the GNU Affero General Public License
#    along with this program. If not, see http://www.gnu.org/licenses/agpl.html
#
##############################################################################

{
    "name": "Mass print GLS attachments after transfer mass action",
    "summary": "Mass print GLS attachments after transfer mass action",
    "version": "14.0.1.0.3",
    "category": "Delivery",
    "website": "https://gitlab.com/tawasta/odoo/delivery",
    "author": "Tawasta",
    "license": "AGPL-3",
    "application": False,
    "installable": True,
    "depends": [
        "delivery_gls_finland",
        "stock_picking_mass_action_print_pdf",
        "web_ir_actions_act_multi",
    ],
    "data": [],
}
