.. image:: https://img.shields.io/badge/licence-AGPL--3-blue.svg
   :target: http://www.gnu.org/licenses/agpl-3.0-standalone.html
   :alt: License: AGPL-3

================================
Delivery Estimated Delivery Time
================================

Adds a field to the sale order to show the estimated delivery 
time for the order. 

* Two new records: 
   * Estimated Delivery Time Rule (base line for estimated delivery time per country)
   * Estimated Delivery Exception (additional exceptions that add x days to the 
     baseline when selected on SO)
* Adds 3 fields to the sale order, all under Other info -> Delivery -tab
   * Estimated Delivery Time
   * Estimated Delivery Time Base
   * Estimated Delivery Time Exception

Configuration
=============

*  Under Sales > Configuration > Estimated Delivery Times you can define rules
   with the destination country and the base minimum and maximum delivery time
   in days. A rule without a destination country acts as a fallback for
   destinations that have no dedicated rule.

*  Under Sales > Configuration > Estimated Delivery Exceptions you can define
   exceptions that can be selected on the sale order. Each exception has a name
   and a number of days that will be added to the base delivery time when selected.

Usage
=====
\-

Known issues / Roadmap
======================
\-

Credits
=======

Contributors
------------

* Joonas Lahtinen <joonas.lahtinen@futural.fi>

Maintainer
----------

.. image:: https://futural.fi/templates/tawastrap/images/logo.png
   :alt: Futural Oy
   :target: https://futural.fi/

This module is maintained by Futural Oy
