# -*- coding: utf-8 -*-
"""
    SOAP v1 smoke tests against a live OpenMage.
"""
import pytest

import magento

from .conftest import API_KEY, API_USER, OPENMAGE_URL

pytestmark = pytest.mark.openmage


def _as_dict(soap_map):
    """Turn a SOAP v1 ``ns2:Map`` (list of key/value items) into a dict."""
    return {entry.key: entry.value for entry in soap_map.item}


@pytest.fixture
def soap_api():
    with magento.API(OPENMAGE_URL, API_USER, API_KEY, protocol='soap') as api:
        yield api


def test_soap_login_and_core_magento_info(soap_api):
    info = _as_dict(soap_api.call('core_magento.info', []))

    assert info['magento_edition'] == 'Community'
    assert 'openmage_version' in info


@pytest.mark.xfail(
    strict=True,
    reason='suds cannot encode a Python list/dict as the xsd:anyType "args" '
           'part (TypeNotFound: args), so SOAP calls that take arguments fail')
def test_soap_call_with_arguments(soap_api):
    soap_api.call('catalog_product.list', [None, None])
