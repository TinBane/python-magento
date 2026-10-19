# -*- coding: utf-8 -*-
from xmlrpc.client import Fault

import pytest

import magento
from magento.utils import camel_2_snake, expand_url

from conftest import PASSWORD, USERNAME


README_APIS = [
    'cart', 'cart_coupon', 'cart_customer', 'cart_payment', 'cart_product',
    'cart_shipping', 'category', 'category_attribute', 'country',
    'credit_memo', 'customer', 'customer_address', 'customer_group',
    'inventory', 'invoice', 'magento', 'order', 'product',
    'product_attribute', 'product_attribute_set', 'product_configurable',
    'product_images', 'product_links', 'product_tier_price',
    'product_types', 'region', 'shipment', 'store',
]


@pytest.mark.parametrize('name', README_APIS)
def test_every_documented_api_is_available_on_the_client(name):
    assert isinstance(getattr(magento.API, name), property)


@pytest.mark.parametrize('url, protocol, expected', [
    ('http://shop.test', 'xmlrpc', 'http://shop.test/index.php/api/xmlrpc'),
    ('http://shop.test/', 'xmlrpc', 'http://shop.test/index.php/api/xmlrpc'),
    ('http://shop.test', 'soap', 'http://shop.test/api/?wsdl'),
])
def test_expand_url(url, protocol, expected):
    assert expand_url(url, protocol) == expected


def test_camel_2_snake():
    assert camel_2_snake('ProductAttributeSet') == 'product_attribute_set'
    assert camel_2_snake('CreditMemo') == 'credit_memo'


def test_context_manager_logs_in_calls_and_ends_session(magento_server):
    with magento.API(magento_server.url, USERNAME, PASSWORD) as api:
        info = api.call('core_magento.info', [])

    assert info['magento_version'] == '1.9.4.5'
    assert magento_server.calls == [('core_magento.info', [])]
    assert magento_server.ended == ['session-1']


def test_sub_api_property_logs_in_once_and_is_reused(magento_server):
    client = magento.API(magento_server.url, USERNAME, PASSWORD)

    assert client.magento.info()['magento_edition'] == 'Community'
    assert client.magento is client.magento
    assert len(magento_server.sessions) == 1


def test_bad_credentials_raise_on_first_call_not_on_connect(magento_server):
    client = magento.API(magento_server.url, USERNAME, 'wrong')
    client.connect()  # builds the proxy only; nothing is sent yet

    with pytest.raises(Fault) as excinfo:
        client.magento.info()
    assert excinfo.value.faultCode == 2


def test_order_search_uses_the_fulfil_extension_resource(magento_server):
    client = magento.API(magento_server.url, USERNAME, PASSWORD)

    with pytest.raises(Fault) as excinfo:
        client.order.search({'status': {'eq': 'pending'}}, limit=10)

    assert excinfo.value.faultString == 'Invalid api path.'
    assert magento_server.calls[-1] == ('sales_order.search', [{
        'imported': False,
        'filters': {'status': {'eq': 'pending'}},
        'fields': [],
        'limit': 10,
        'page': 1,
    }])


def test_order_list_uses_the_stock_resource(magento_server):
    magento_server.responses['sales_order.list'] = [{'increment_id': '1'}]
    client = magento.API(magento_server.url, USERNAME, PASSWORD)

    assert client.order.list({'status': {'eq': 'pending'}}) == [
        {'increment_id': '1'}]
    assert magento_server.calls[-1] == (
        'sales_order.list', [{'status': {'eq': 'pending'}}])


def test_product_create_sends_type_set_sku_and_data(magento_server):
    magento_server.responses['catalog_product.create'] = '42'
    client = magento.API(magento_server.url, USERNAME, PASSWORD)

    data = {'name': 'Mug', 'price': '9.95', 'websites': [1], 'status': 1}
    assert client.product.create('simple', 4, 'MUG-1', data) == 42
    assert magento_server.calls[-1] == (
        'catalog_product.create', ['simple', 4, 'MUG-1', data])


def test_multicall(magento_server):
    with magento.API(magento_server.url, USERNAME, PASSWORD) as api:
        result = api.multiCall([['core_magento.info', []]])
    assert result[0]['magento_version'] == '1.9.4.5'
