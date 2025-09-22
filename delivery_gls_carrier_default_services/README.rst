.. image:: https://img.shields.io/badge/licence-AGPL--3-blue.svg
   :target: http://www.gnu.org/licenses/agpl-3.0-standalone.html
   :alt: License: AGPL-3

============================
GLS Carrier Default Services
============================

Add services automatically when using GLS Carrier. Currently supports adding
services to picking orders when picking order is created and adding services
to picking orders when created when Customer has Delivery Email set.

Configuration
=============

Odoo
----
1. Go to Inventory->Configuration->Delivery->Shipping methods
2. Add Carrier or open existing one
3. Fill in either "Add services to picking order" or "Add services to picking
   order when customer has delivery email"

Usage
=====
1. Create a sale with a carrier (or manually create a delivery)


Known issues / Roadmap
======================
\-

Credits
=======

Contributors
------------

* Joona Isoaho <joona.isoaho@futural.fi>

Maintainer
----------

.. image:: https://futural.fi/templates/tawastrap/images/logo.png
   :alt: Futural Oy.
   :target: https://futural.fi/

This module is maintained by Futural Oy.
