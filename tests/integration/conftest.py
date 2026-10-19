# -*- coding: utf-8 -*-
"""
    Fixtures for the opt-in OpenMage integration tests.

    These tests talk to a real OpenMage install (see dev/openmage). They are
    skipped unless OPENMAGE_URL is set, so the default test run stays offline.
"""
import os

import pytest

import magento

OPENMAGE_URL = os.environ.get('OPENMAGE_URL')
API_USER = os.environ.get('OPENMAGE_API_USER', 'pytest')
API_KEY = os.environ.get('OPENMAGE_API_KEY', 'pytest-api-key-123')

# Seeded by dev/openmage/scripts/seed.php.
PRODUCT_SKU = 'pytest-simple'
CUSTOMER_EMAIL = 'pytest.customer@example.com'
STORE = 'default'
NO_EMAIL_STORE = 'noemail'

US_ADDRESS = {
    'firstname': 'Guest',
    'lastname': 'Buyer',
    'street': '1 Test Street',
    'city': 'Austin',
    'region': 'Texas',
    'region_id': '57',
    'postcode': '73301',
    'country_id': 'US',
    'telephone': '5125550100',
}


def pytest_collection_modifyitems(config, items):
    if OPENMAGE_URL:
        return
    skip = pytest.mark.skip(
        reason='set OPENMAGE_URL to run against a live OpenMage '
               '(see dev/openmage/bootstrap.sh)')
    for item in items:
        if 'openmage' in item.keywords:
            item.add_marker(skip)


@pytest.fixture(scope='session')
def client():
    with magento.API(OPENMAGE_URL, API_USER, API_KEY) as api:
        yield api


@pytest.fixture(scope='session')
def customer(client):
    found = client.customer.list({'email': {'eq': CUSTOMER_EMAIL}})
    assert found, 'seeded customer missing; re-run dev/openmage/bootstrap.sh'
    customer = found[0]
    customer['address'] = client.customer_address.list(
        int(customer['customer_id']))[0]
    return customer


@pytest.fixture
def quote(client):
    """A fresh cart in the default store view holding one seeded product."""
    quote_id = client.cart.create(STORE)
    assert client.cart_product.add(
        quote_id, [{'sku': PRODUCT_SKU, 'qty': 1}], STORE)
    return quote_id
