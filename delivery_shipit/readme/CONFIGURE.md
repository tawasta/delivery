## ShipIT configuration

1. After installing, go to `Settings > ShipIT`
2. Fill in your `API key` and save settings
3. Go back to `Settings > ShipIT` and click `Sync ShipIT services`

   ![ShipIT settings](../static/description/shipit_settings.png)


## Shipping methods

This will fetch the available services and create them in `Shipping methods`.
You can go to `Inventory > Configuration > Delivery > Shipping Methods` and see what's available and configure them further.

`ShipIT Allowed Additional Services` are updated automatically when you sync ShipIT services
`ShipIT Allowed Package Types` need to be applied manually at the moment
`ShipIT Default Additional Services` can be set to always suggest certain service on new deliveries using this shipping method

   ![ShipIT shipping method](../static/description/shipit_shipping_method.png)


## Package types

If you use packaging, you can configure different package types to use.
Go to `Inventory > Configuration > Package Types`

You can create carrier-spesific package types here.
Regarding ShipIT, the important part is `ShipIT Package Type`.
Available package types are listed there, and you should pick one.

   ![ShipIT package type](../static/description/shipit_package_type.png)

After that you can use that package type with the carrier.
You can also limit the available package types in `Shipping methods` (see previous step).