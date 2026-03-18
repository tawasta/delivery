.. image:: https://img.shields.io/badge/licence-AGPL--3-blue.svg
   :target: http://www.gnu.org/licenses/agpl-3.0-standalone.html
   :alt: License: AGPL-3

===============
ShipIT Shipping
===============

ShipIT delivery carrier skeleton for Odoo 17.

Configuration
=============

1. Go to Inventory -> Configuration -> Delivery -> Shipping Methods
2. Create or open a carrier
3. Set Provider to ``ShipIT``
4. Fill in ShipIT configuration fields
5. Optionally adjust advanced API settings (base URL, endpoints, auth mode, timeout)
6. Enable ``Store ShipIT debug payloads`` if you want request/response payloads
   persisted to picking fields for troubleshooting

The module also installs a default delivery product and a ``ShipIT Default`` carrier
template that can be used as a starting point.

Local setup notes
=================

To use this addon in the current local workspace, Odoo must include both project
and delivery addon paths. Example:

* ``docker-compose.yml``:

  * ``./project:/mnt/extra-addons``
  * ``./delivery:/mnt/delivery-addons``

* ``config/odoo.conf``:

  * ``addons_path = /mnt/extra-addons,/mnt/delivery-addons``

Usage
=====

This version implements a first ShipIT happy path:

1. Validate required sender/recipient/carrier fields
2. Build shipment payload from picking data
3. Create shipment via ShipIT v1 API (``PUT /v1/shipment`` with ``X-SHIPIT-KEY``)
4. Store shipment id, tracking data and label attachment to picking
5. Trigger shipment creation from delivery ``Validate`` action for ShipIT carriers
6. Store request/response debug payloads to picking fields
7. Download label document from ``freightDoc`` URL when available
8. Optional fallback to separate label endpoint if configured
9. Search pickup points via ShipIT ``POST /agents`` and save selected point
10. Optional carrier-level pickup point requirement before shipment create
11. Only trigger API calls automatically for outgoing pickings

Manual test checklist
=====================

1. Create/verify a ShipIT carrier with API key, reseller ID and service ID.
2. Create a delivery order with ShipIT as carrier.
3. Optional pickup test:

   * click ``Hae noutopiste`` on picking
   * search points and select one
   * verify pickup fields are stored on picking

4. Run ``Validate`` on the delivery.
5. Verify:

   * ``shipit_shipment_id`` is set
   * ``shipit_tracking_codes`` is set
   * label attachment exists on the picking

6. Negative test: remove recipient phone/email and validate that user-facing
   validation error is shown before API call.

Known issues / Roadmap
======================

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
