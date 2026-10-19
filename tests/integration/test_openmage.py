# -*- coding: utf-8 -*-
"""
    Smoke and checkout tests against a live OpenMage over XML-RPC.
"""
import pytest

from .conftest import CUSTOMER_EMAIL, PRODUCT_SKU, STORE, US_ADDRESS

pytestmark = pytest.mark.openmage


def test_core_magento_info(client):
    info = client.magento.info()

    assert info['magento_edition'] == 'Community'
    assert info['magento_version'].startswith('1.9')
    assert 'openmage_version' in info


def test_product_list_and_info(client):
    products = client.product.list({'sku': {'eq': PRODUCT_SKU}})
    assert [p['sku'] for p in products] == [PRODUCT_SKU]

    info = client.product.info(PRODUCT_SKU, identifierType='sku')
    assert info['product_id'] == products[0]['product_id']
    assert info['type'] == 'simple'
    assert float(info['price']) == 10.0


def test_customer_list(client):
    customers = client.customer.list({'email': {'eq': CUSTOMER_EMAIL}})

    assert len(customers) == 1
    assert customers[0]['firstname'] == 'Pytest'


def test_order_list(client):
    assert isinstance(client.order.list(), list)


def test_cart_checkout_as_registered_customer(client, customer, quote):
    address_id = customer['address']['customer_address_id']

    assert client.cart_customer.set(quote, {
        'mode': 'customer',
        'customer_id': customer['customer_id'],
    }, STORE)
    assert client.cart_customer.addresses(quote, [
        {'mode': 'billing', 'address_id': address_id},
        {'mode': 'shipping', 'address_id': address_id},
    ], STORE)

    rates = client.cart_shipping.list(quote, STORE)
    assert 'flatrate_flatrate' in [rate['code'] for rate in rates]
    assert client.cart_shipping.method(quote, 'flatrate_flatrate', STORE)

    methods = client.cart_payment.list(quote, STORE)
    assert 'checkmo' in [method['code'] for method in methods]
    assert client.cart_payment.method(quote, {'method': 'checkmo'}, STORE)

    totals = {t['title']: float(t['amount'])
              for t in client.cart.totals(quote, STORE)}
    assert totals['Grand Total'] == 15.0  # 10.00 product + 5.00 flat rate

    increment_id = client.cart.order(quote, STORE)

    order = client.order.info(increment_id)
    assert order['customer_email'] == CUSTOMER_EMAIL
    assert order['shipping_method'] == 'flatrate_flatrate'
    assert order['payment']['method'] == 'checkmo'
    assert float(order['grand_total']) == 15.0
    assert [item['sku'] for item in order['items']] == [PRODUCT_SKU]
    assert [o['increment_id'] for o in client.order.list(
        {'increment_id': {'eq': increment_id}})] == [increment_id]


def test_cart_checkout_as_guest(client, quote):
    assert client.cart_customer.set(quote, {
        'mode': 'guest',
        'firstname': 'Guest',
        'lastname': 'Buyer',
        'email': 'guest.buyer@example.com',
    }, STORE)
    assert client.cart_customer.addresses(quote, [
        dict(US_ADDRESS, mode='billing'),
        dict(US_ADDRESS, mode='shipping'),
    ], STORE)
    assert client.cart_shipping.method(quote, 'flatrate_flatrate', STORE)
    assert client.cart_payment.method(quote, {'method': 'checkmo'}, STORE)

    increment_id = client.cart.order(quote, STORE)

    order = client.order.info(increment_id)
    assert order['customer_is_guest'] == '1'
    assert order['customer_email'] == 'guest.buyer@example.com'
