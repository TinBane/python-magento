# -*- coding: utf-8 -*-
"""
    Reproductions of upstream fulfilio/python-magento checkout issues against a
    live OpenMage. Each test pins down what the server actually does, and the
    call sequence that works.
"""
from xml.parsers.expat import ExpatError
from xmlrpc.client import Fault, ProtocolError

import pytest

from .conftest import NO_EMAIL_STORE, PRODUCT_SKU, STORE, US_ADDRESS

pytestmark = pytest.mark.openmage

GUEST = {
    'mode': 'guest',
    'firstname': 'Guest',
    'lastname': 'Buyer',
    'email': 'guest.buyer@example.com',
}


def _fault_code(excinfo):
    return excinfo.value.faultCode


# --- #28 "could not set customer data in CartCustomer" -----------------------

def test_issue_28_unknown_mode_crashes_the_server(client, quote):
    # 'admin' is not a checkout mode. Magento's switch has no default branch,
    # so $customer stays unset and Quote::setCustomer(null) dies: Fault 1
    # "Internal Error" on PHP 5, an uncaught TypeError (HTTP 500) on PHP 8.
    data = dict(GUEST, mode='admin')
    with pytest.raises((Fault, ProtocolError, ExpatError)):
        client.cart_customer.set(quote, data, STORE)


def test_issue_28_missing_mode_is_rejected(client, quote):
    data = {k: v for k, v in GUEST.items() if k != 'mode'}
    with pytest.raises(Fault) as excinfo:
        client.cart_customer.set(quote, data, STORE)
    assert _fault_code(excinfo) == 1045  # Customer's mode is unknown


@pytest.mark.parametrize('data', [
    GUEST,
    dict(GUEST, mode='register', email='register.buyer@example.com',
         password='pytest-password-123'),
], ids=['guest', 'register'])
def test_issue_28_valid_modes_work(client, quote, data):
    assert client.cart_customer.set(quote, data, STORE)


def test_issue_28_customer_mode_needs_customer_id(client, customer, quote):
    assert client.cart_customer.set(quote, {
        'mode': 'customer', 'customer_id': customer['customer_id']}, STORE)


# --- #29 "Fault 1062: Shipping method is not available" ----------------------

@pytest.fixture
def addressed_quote(client, quote):
    client.cart_customer.set(quote, GUEST, STORE)
    client.cart_customer.addresses(quote, [
        dict(US_ADDRESS, mode='billing'),
        dict(US_ADDRESS, mode='shipping'),
    ], STORE)
    return quote


@pytest.mark.parametrize('wrong', [
    {'method': 'flatrate'},  # a dict, as in the issue
    'flatrate',              # the carrier, not the rate code
    'Flat Rate',             # the title
], ids=['dict', 'carrier', 'title'])
def test_issue_29_shipping_method_must_be_the_rate_code(
        client, addressed_quote, wrong):
    with pytest.raises(Fault) as excinfo:
        client.cart_shipping.method(addressed_quote, wrong, STORE)
    assert _fault_code(excinfo) == 1062


def test_issue_29_rate_code_from_list_works(client, addressed_quote):
    codes = [r['code'] for r in client.cart_shipping.list(
        addressed_quote, STORE)]
    assert 'flatrate_flatrate' in codes
    assert client.cart_shipping.method(
        addressed_quote, 'flatrate_flatrate', STORE)


def test_issue_29_shipping_needs_an_address_first(client, quote):
    with pytest.raises(Fault) as excinfo:
        client.cart_shipping.method(quote, 'flatrate_flatrate', STORE)
    assert _fault_code(excinfo) == 1061  # shipping address is not set


# --- #32 "Disable email sending for new orders" ------------------------------

def _place_guest_order(client, store):
    quote = client.cart.create(store)
    client.cart_product.add(quote, [{'sku': PRODUCT_SKU, 'qty': 1}], store)
    client.cart_customer.set(quote, GUEST, store)
    client.cart_customer.addresses(quote, [
        dict(US_ADDRESS, mode='billing'),
        dict(US_ADDRESS, mode='shipping'),
    ], store)
    client.cart_shipping.method(quote, 'flatrate_flatrate', store)
    client.cart_payment.method(quote, {'method': 'checkmo'}, store)
    return client.order.info(client.cart.order(quote, store))


def test_issue_32_order_email_follows_store_config(client):
    # cart.order has no "don't email" argument; it always calls
    # Order::queueNewOrderEmail(), which only checks the store's
    # sales_email/order/enabled setting. The seed script turns that off for
    # the "noemail" store view, so orders placed there are not emailed.
    emailed = _place_guest_order(client, STORE)
    silent = _place_guest_order(client, NO_EMAIL_STORE)

    assert emailed['email_sent'] == '1'
    assert not silent['email_sent']
