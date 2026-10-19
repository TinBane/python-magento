Magento Python API
==================

Python client for the Magento 1 Core API (XML-RPC and SOAP). It works with
Magento 1.x and with `OpenMage LTS <https://www.openmage.org/>`_, the
maintained continuation of Magento 1.

This is a maintained fork of `fulfilio/python-magento
<https://github.com/fulfilio/python-magento>`_, which has had no release
since 2019. Version 4.0 runs on Python 3.9 and later and replaces the
unmaintained ``suds-jurko`` dependency with ``suds-community``, so it
installs on current Python and setuptools again.

**Magento 2 / Adobe Commerce:** this library talks to the Magento 1 API.
For Magento 2 use `PyMagento <https://github.com/Bixoto/PyMagento>`_.

Installation
------------

.. code-block:: sh

    pip install magento1-client

The package is published as ``magento1-client`` but is still imported as
``magento``, so existing code keeps working. Uninstall the old ``magento``
package first (``pip uninstall magento``); both install the same
``magento`` module. PyMagento also installs a ``magento`` module, so it
cannot be installed alongside this one.

Credentials
-----------

The username and password are those of a *Web Services* user, not a
Magento admin login. Create one in the Magento admin under
*System > Web Services > SOAP/XML-RPC - Users*, and give it a role under
*SOAP/XML-RPC - Roles* that allows the resources you need.

Usage
-----

.. code-block:: python

    import magento

    url = 'http://domain.com/'
    apiuser = 'user'
    apipass = 'password'

    # Create an instance of API
    client = magento.API(url, apiuser, apipass)

    # A filter expression as dictionary.
    product_filter = {'created_at': {'from': '2011-09-15 00:00:00'}}
    products = client.product.list(product_filter)

    # Get a list of product types
    product_types = client.product_types.list()

    # Get a specific product
    sku = 'prod1'
    product = client.product.info(sku)

    # Add comment to an order
    order_increment_id = '100000001'
    status = 'canceled'
    client.order.addcomment(order_increment_id, status)

Each API (``client.product``, ``client.order``, ...) logs in the first
time you use it and keeps its session for later calls.

Checking the connection
-----------------------

``client.connect()`` only builds the connection object; it does not
contact Magento. To check that the URL and credentials work, make a cheap
call and catch the error:

.. code-block:: python

    from xmlrpc.client import Fault, ProtocolError

    client = magento.API(url, apiuser, apipass)
    try:
        info = client.magento.info()
    except Fault as e:
        # e.g. Fault 2 'Access denied.' for a wrong user or API key
        print('Magento refused the call:', e.faultCode, e.faultString)
    except (ProtocolError, OSError) as e:
        # wrong URL (e.g. 404 at index.php/api/xmlrpc) or host unreachable
        print('Could not reach the API:', e)
    else:
        print('Connected to Magento', info['magento_version'])

Filters
-------

The ``list`` methods take filters in Magento's
``{<attribute>: {<operator>: <value>}}`` format, for example
``{'status': {'eq': 'pending'}}`` or ``{'sku': {'like': 'MUG-%'}}``.
Operators include ``eq``, ``neq``, ``like``, ``in``, ``nin``, ``gt``,
``lt``, ``gteq``, ``lteq``, ``from`` and ``to``.

Creating a product
------------------

``client.product.create(product_type, attribute_set_id, sku, data)``
takes the product type (``'simple'``, ``'configurable'``, ...), the ID of
an attribute set, the SKU, and a dictionary of attribute values. The SKU
is passed on its own and does not go in ``data``.

.. code-block:: python

    # Find the attribute set to use ('Default' is usually 4)
    attribute_sets = client.product_attribute_set.list()

    product_id = client.product.create('simple', 4, 'MUG-1', {
        'name': 'Coffee mug',
        'description': 'A large coffee mug',
        'short_description': 'Coffee mug',
        'price': '9.95',
        'weight': '0.4',
        'status': 1,            # 1 = enabled, 2 = disabled
        'visibility': 4,        # 4 = catalog and search
        'tax_class_id': 2,      # 2 = taxable goods on a default install
        'websites': [1],
        'stock_data': {'qty': 10, 'is_in_stock': 1},
    })

``Fault 102: 'Invalid data given'`` usually means a required attribute of
the attribute set is missing from ``data``, or a value has the wrong
format. Look at an existing product with ``client.product.info(sku)`` to
see the attribute names and formats your store expects.

Placing an order through the cart API
-------------------------------------

The cart calls have to run in this order, all with the same store view.
Without ``store_view`` the cart is created in the admin store (ID 0), and
the order ends up there too.

.. code-block:: python

    store = 'default'   # store view code or ID
    address = {
        'firstname': 'Jane', 'lastname': 'Doe', 'street': '1 Main Street',
        'city': 'Austin', 'region_id': '57', 'postcode': '73301',
        'country_id': 'US', 'telephone': '5125550100',
    }

    quote = client.cart.create(store)
    client.cart_product.add(quote, [{'sku': 'MUG-1', 'qty': 1}], store)
    client.cart_customer.set(quote, {
        'mode': 'guest',
        'firstname': 'Jane', 'lastname': 'Doe',
        'email': 'jane@example.com',
    }, store)
    client.cart_customer.addresses(quote, [
        dict(address, mode='billing'),
        dict(address, mode='shipping'),
    ], store)

    # Pick a rate code from the list, e.g. 'flatrate_flatrate'
    rates = client.cart_shipping.list(quote, store)
    client.cart_shipping.method(quote, rates[0]['code'], store)

    client.cart_payment.method(quote, {'method': 'checkmo'}, store)
    order_increment_id = client.cart.order(quote, store)

Common errors:

* **Setting the customer fails** (fulfilio#28). ``mode`` must be
  ``'guest'``, ``'register'`` (also needs ``password``) or ``'customer'``
  (needs ``customer_id`` of an existing customer). A missing mode gives
  ``Fault 1045``; any other value, such as ``'admin'``, crashes inside
  Magento (``Fault 1`` or an HTTP 500 on PHP 8).
* **Fault 1062: 'Shipping method is not available'** (fulfilio#29).
  ``cart_shipping.method`` takes the rate ``code`` string from
  ``cart_shipping.list`` (``'flatrate_flatrate'``), not the carrier name,
  title or a dictionary. ``Fault 1061`` means the shipping address has not
  been set yet.

Placing orders without sending the order email
----------------------------------------------

``cart.order`` cannot skip the new-order email (fulfilio#32): Magento
always sends it when *System > Configuration > Sales Emails > Order >
Enabled* is on for the store view. To place orders silently, create a
store view for API orders, set that option to *No* for it, and pass that
store view's code to every ``cart.*`` call. Note that the *Send Email*
button on the admin order page checks the same setting, so it will not
send emails for orders in that store view either.

Searching orders
----------------

``client.order.search()`` calls ``sales_order.search``, which is not part
of the stock Magento 1 API. It needs the Fulfil.IO / Openlabs connector
extension on the Magento side; without it Magento answers
``Fault 3: Invalid api path``. On a stock install use
``client.order.list(filters)`` instead.

All available APIs
-------------------

* Cart (`client.cart`)
* CartCoupon (`client.cart_coupon`)
* CartCustomer (`client.cart_customer`)
* CartPayment (`client.cart_payment`)
* CartProduct (`client.cart_product`)
* CartShipping (`client.cart_shipping`)
* Category (`client.category`)
* CategoryAttribute (`client.category_attribute`)
* Country (`client.country`)
* CreditMemo (`client.credit_memo`)
* Customer (`client.customer`)
* CustomerAddress (`client.customer_address`)
* CustomerGroup (`client.customer_group`)
* Inventory (`client.inventory`)
* Invoice (`client.invoice`)
* Magento (`client.magento`)
* Order (`client.order`)
* Product (`client.product`)
* ProductAttribute (`client.product_attribute`)
* ProductAttributeSet (`client.product_attribute_set`)
* ProductConfigurable (`client.product_configurable`)
* ProductImages (`client.product_images`)
* ProductLinks (`client.product_links`)
* ProductTierPrice (`client.product_tier_price`)
* ProductTypes (`client.product_types`)
* Region (`client.region`)
* Shipment (`client.shipment`)
* Store (`client.store`)

Old style: one API object per resource
--------------------------------------

The API was originally written with the requirement to call APIs
individually with all the credentials. This led to very verbose code and a
lot of repetition. While the behavior has not been deprecated, it is
recommended to write all new code with the pattern shown in the above
example.

.. code-block:: python

    import magento

    url = 'http://domain.com/'
    apiuser = 'user'
    apipass = 'password'

    with magento.Order(url, apiuser, apipass) as order_api:
        order_increment_id = '100000001'
        status = 'canceled'
        order_api.addcomment(order_increment_id, status)

    with magento.Store(url, apiuser, apipass) as store_api:
        store_id = '1'
        store_view_info = store_api.info(store_id)
        store_views = store_api.list()

    with magento.Magento(url, apiuser, apipass) as magento_api:
        magento_info = magento_api.info()


Calling custom classes from your own API extensions
---------------------------------------------------

You can directly invoke the underlying `call` method
to make calls directly. Unlike the named APIs above, the client itself
only logs in inside a ``with`` block:

.. code-block:: python

    with client:
        result = client.call('custom_model.list', [])


Alternatively, you can also build sub classes of API to have
a more pythonic structure. The subclasses are automatically
registered with API when classes are created. 

To ensure that they are registered before you create the first API
instance, always have all your imports on the top of your magento module.

.. code-block:: python

    from magento.api import API

    class CustomModel(API):
        def list(self):
            return self.call('custom_model.list', [])

which would be automatically registered as `custom_model` by the API
metaclass. So you can now use

.. code-block:: python

    import magento
    from my_custom_module import CustomModel

    url = 'http://domain.com/'
    apiuser = 'user'
    apipass = 'password'

    # Create an instance of API
    client = magento.API(url, apiuser, apipass)
    
    client.custom_model.list()

Protocols
---------

XML-RPC is the default. Pass ``protocol='soap'`` to use the SOAP v1 API
instead:

.. code-block:: python

    client = magento.API(url, apiuser, apipass, protocol='soap')

SOAP support is limited: suds cannot encode list or dictionary arguments
for Magento's SOAP v1 API, so only calls without arguments (such as
``client.magento.info()``) work over SOAP. Use XML-RPC for everything
else.

A minimal ``protocol='rest'`` client for the Magento 2 REST API is also
included, but it only supports GET requests and needs ``requests``
installed (the ``rest`` extra). For Magento 2 work, PyMagento is the better choice.

Integration tests
-----------------

``uv run pytest -q`` runs offline against a stand-in for the XML-RPC API,
and skips the tests in ``tests/integration``. Those run against a real
OpenMage LTS that ``dev/openmage/bootstrap.sh`` sets up in Docker (PHP 8.3
with Apache, plus MariaDB). The first run downloads and installs OpenMage
and creates a test-only API user, a product, a customer, and the flat rate
and check/money order methods; later runs reuse the install. The test
credentials are in ``dev/openmage/.env.example``, which the script copies to
``.env``.

.. code-block:: sh

    dev/openmage/bootstrap.sh
    OPENMAGE_URL=http://localhost:18080/ uv run pytest -q -m openmage
    docker compose -f dev/openmage/docker-compose.yml stop    # keeps the install
    docker compose -f dev/openmage/docker-compose.yml start   # resume later
    dev/openmage/bootstrap.sh --reset                          # wipe and reinstall

License
-------

BSD 3-Clause

See LICENSE for more details
