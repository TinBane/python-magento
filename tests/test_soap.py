# -*- coding: utf-8 -*-
"""
    SOAP v1 client construction against a Magento/OpenMage-style WSDL.
"""
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer

import pytest

import magento

# Trimmed from the WSDL OpenMage 20.x serves at /api/?wsdl. As in stock
# Magento since 1.4.2, the soapenc import is commented out while FixedArray
# still restricts soapenc:Array.
OPENMAGE_STYLE_WSDL = b"""<?xml version="1.0" encoding="UTF-8"?>
<definitions xmlns:typens="urn:OpenMage"
    xmlns:xsd="http://www.w3.org/2001/XMLSchema"
    xmlns:soap="http://schemas.xmlsoap.org/wsdl/soap/"
    xmlns:soapenc="http://schemas.xmlsoap.org/soap/encoding/"
    xmlns:wsdl="http://schemas.xmlsoap.org/wsdl/"
    xmlns="http://schemas.xmlsoap.org/wsdl/"
    name="OpenMage" targetNamespace="urn:OpenMage">
    <types>
        <schema xmlns="http://www.w3.org/2001/XMLSchema"
            targetNamespace="urn:OpenMage">
<!--        <import namespace="http://schemas.xmlsoap.org/soap/encoding/"
                schemaLocation="http://schemas.xmlsoap.org/soap/encoding/" />-->
            <complexType name="FixedArray">
                <complexContent>
                    <restriction base="soapenc:Array">
                        <attribute ref="soapenc:arrayType"
                            wsdl:arrayType="xsd:anyType[]" />
                    </restriction>
                </complexContent>
            </complexType>
        </schema>
    </types>
    <message name="call">
        <part name="sessionId" type="xsd:string" />
        <part name="resourcePath" type="xsd:string" />
        <part name="args" type="xsd:anyType" />
    </message>
    <message name="callResponse">
        <part name="callReturn" type="xsd:anyType" />
    </message>
    <message name="login">
        <part name="username" type="xsd:string" />
        <part name="apiKey" type="xsd:string" />
    </message>
    <message name="loginResponse">
        <part name="loginReturn" type="xsd:string" />
    </message>
    <message name="resources">
        <part name="sessionId" type="xsd:string" />
    </message>
    <message name="resourcesResponse">
        <part name="resourcesReturn" type="typens:FixedArray" />
    </message>
    <portType name="PortType">
        <operation name="call">
            <input message="typens:call" />
            <output message="typens:callResponse" />
        </operation>
        <operation name="login">
            <input message="typens:login" />
            <output message="typens:loginResponse" />
        </operation>
        <operation name="resources">
            <input message="typens:resources" />
            <output message="typens:resourcesResponse" />
        </operation>
    </portType>
    <binding name="Binding" type="typens:PortType">
        <soap:binding style="rpc" transport="http://schemas.xmlsoap.org/soap/http" />
        <operation name="call">
            <soap:operation soapAction="urn:Mage_Api_Model_Server_HandlerAction" />
            <input><soap:body namespace="urn:OpenMage" use="encoded"
                encodingStyle="http://schemas.xmlsoap.org/soap/encoding/" /></input>
            <output><soap:body namespace="urn:OpenMage" use="encoded"
                encodingStyle="http://schemas.xmlsoap.org/soap/encoding/" /></output>
        </operation>
        <operation name="login">
            <soap:operation soapAction="urn:Mage_Api_Model_Server_HandlerAction" />
            <input><soap:body namespace="urn:OpenMage" use="encoded"
                encodingStyle="http://schemas.xmlsoap.org/soap/encoding/" /></input>
            <output><soap:body namespace="urn:OpenMage" use="encoded"
                encodingStyle="http://schemas.xmlsoap.org/soap/encoding/" /></output>
        </operation>
        <operation name="resources">
            <soap:operation soapAction="urn:Mage_Api_Model_Server_HandlerAction" />
            <input><soap:body namespace="urn:OpenMage" use="encoded"
                encodingStyle="http://schemas.xmlsoap.org/soap/encoding/" /></input>
            <output><soap:body namespace="urn:OpenMage" use="encoded"
                encodingStyle="http://schemas.xmlsoap.org/soap/encoding/" /></output>
        </operation>
    </binding>
    <service name="OpenMageService">
        <port name="Port" binding="typens:Binding">
            <soap:address location="http://127.0.0.1/api/" />
        </port>
    </service>
</definitions>
"""


class _WsdlHandler(BaseHTTPRequestHandler):

    def do_GET(self):
        self.send_response(200)
        self.send_header('Content-Type', 'text/xml; charset=UTF-8')
        self.end_headers()
        self.wfile.write(OPENMAGE_STYLE_WSDL)

    def log_message(self, *args):
        pass


@pytest.fixture
def wsdl_url():
    server = HTTPServer(('127.0.0.1', 0), _WsdlHandler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        yield 'http://127.0.0.1:%d/' % server.server_address[1]
    finally:
        server.shutdown()
        server.server_close()


def test_soap_connect_handles_wsdl_without_soapenc_import(wsdl_url):
    # Regression: suds raised TypeNotFound '(Array, http://schemas.xmlsoap.org
    # /soap/encoding/, )' for every Magento >= 1.4.2 / OpenMage WSDL.
    client = magento.API(wsdl_url, 'apiuser', 'apikey', protocol='soap')
    client.connect()

    methods = {m.name for m in
               client.client.wsdl.services[0].ports[0].methods.values()}
    assert {'call', 'login', 'resources'} <= methods
