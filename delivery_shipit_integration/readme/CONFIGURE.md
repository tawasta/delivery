## Shipit configuration

1. After installing, go to `Settings > Shipit`
2. Fill in your `API key` and save settings
3. Go back to `Settings > Shipit` and click `Sync Shipit services`

   ![Shipit settings](../static/description/shipit_settings.png)


## Shipping methods

This will fetch the available services and create them in `Shipping methods`.
You can go to `Inventory > Configuration > Delivery > Shipping Methods` and see what's available and configure them further.

`Shipit Allowed Additional Services` are updated automatically when you sync Shipit services
`Shipit Allowed Package Types` need to be applied manually at the moment
`Shipit Default Additional Services` can be set to always suggest certain service on new deliveries using this shipping method

   ![Shipit shipping method](../static/description/shipit_shipping_method.png)


## Package types

If you use packaging, you can configure different package types to use.
Go to `Inventory > Configuration > Package Types`

You can create carrier-spesific package types here.
Regarding Shipit, the important part is `Shipit Package Type`.
Available package types are listed there, and you should pick one.

   ![Shipit package type](../static/description/shipit_package_type.png)

After that you can use that package type with the carrier.
You can also limit the available package types in `Shipping methods` (see previous step).