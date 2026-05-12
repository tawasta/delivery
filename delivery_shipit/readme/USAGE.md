Usage
=====

This module implements the ShipIT integration flow:

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