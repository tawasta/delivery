Configuration
=============

1. Go to Inventory -> Configuration -> Delivery -> Shipping Methods
2. Create or open a carrier
3. Set Provider to ``ShipIT``
4. Fill in ShipIT configuration fields (API key, reseller ID, service IDs)
5. Enable ``Store ShipIT debug payloads`` if you want request/response payloads
   persisted to picking fields for troubleshooting

The module also installs a default delivery product and a ``ShipIT`` carrier
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

Manual test checklist
=====================

1. Create/verify a ShipIT carrier with API key, reseller ID and service ID.
2. Create a delivery order with ShipIT as carrier.
3. Optional pickup test:

   * click ``Select`` on picking ``Pickup point``
   * search pickup points and select one
   * verify pickup fields are stored on picking

4. Run ``Validate`` on the delivery.
5. Verify:

   * ``shipit_shipment_id`` is set
   * ``shipit_tracking_codes`` is set
   * label attachment exists on the picking

6. Negative test: remove recipient phone/email and validate that user-facing
   validation error is shown before API call.