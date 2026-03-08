.. image:: https://img.shields.io/badge/licence-AGPL--3-blue.svg
   :target: http://www.gnu.org/licenses/agpl-3.0-standalone.html
   :alt: License: AGPL-3

==============
ShipIT Shipping
==============

ShipIT delivery carrier skeleton for Odoo 17.

Configuration
=============

1. Go to Inventory -> Configuration -> Delivery -> Shipping Methods
2. Create or open a carrier
3. Set Provider to ``ShipIT``
4. Fill in ShipIT configuration fields
5. Optionally adjust advanced API settings (base URL, endpoints, auth mode, timeout)

Usage
=====

This version implements a first ShipIT happy path:

1. Validate required sender/recipient/carrier fields
2. Build shipment payload from picking data
3. Create shipment via ShipIT API
4. Store shipment id, tracking data and label attachment to picking
5. Trigger shipment creation from delivery ``Validate`` action for ShipIT carriers

Known issues / Roadmap
======================

* Improve response mapping for endpoint-specific payloads
* Add pickup point support
* Add multi-package support

Credits
=======

Contributors
------------

* ShipIT integration team

Maintainer
----------

.. image:: https://tawasta.fi/templates/tawastrap/images/logo.png
   :alt: Oy Tawasta OS Technologies Ltd.
   :target: https://tawasta.fi/

This module is maintained by Oy Tawasta OS Technologies Ltd.
