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
    "name": "GLS Finland Shipping",
    "summary": "Send your shipments through GLS Finland and track them online",
    "version": "14.0.1.2.5",
    "category": "Connector",
    "website": "https://gitlab.com/tawasta/odoo/delivery",
    "author": "Tawasta",
    "license": "AGPL-3",
    "application": False,
    "installable": True,
    "depends": ["delivery", "mail", "stock_picking_comment"],
    "data": [
        "data/delivery_carrier.xml",
        "views/delivery_carrier.xml",
        "views/stock_picking.xml",
    ],
}
