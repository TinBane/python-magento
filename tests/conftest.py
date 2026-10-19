# -*- coding: utf-8 -*-
"""
    A stand-in for the Magento 1 XML-RPC endpoint.

    It speaks the same login / call / multiCall / endSession protocol as
    ``index.php/api/xmlrpc`` and records every call so tests can check what
    the client actually sent over the wire.
"""
import threading
from xmlrpc.server import SimpleXMLRPCServer, SimpleXMLRPCRequestHandler
from xmlrpc.client import Fault

import pytest

USERNAME = 'apiuser'
PASSWORD = 'apikey'


class FakeMagento(object):

    def __init__(self):
        self.calls = []
        self.sessions = set()
        self.ended = []
        self.responses = {
            'core_magento.info': {
                'magento_edition': 'Community', 'magento_version': '1.9.4.5',
            },
        }

    def login(self, username, password):
        if (username, password) != (USERNAME, PASSWORD):
            raise Fault(2, 'Access denied.')
        session = 'session-%d' % (len(self.sessions) + 1)
        self.sessions.add(session)
        return session

    def endSession(self, session):
        self.ended.append(session)
        self.sessions.discard(session)
        return True

    def call(self, session, resource_path, arguments):
        if session not in self.sessions:
            raise Fault(5, 'Session expired. Try to relogin.')
        self.calls.append((resource_path, arguments))
        if resource_path not in self.responses:
            raise Fault(3, 'Invalid api path.')
        return self.responses[resource_path]

    def multiCall(self, session, calls):
        # Magento reports a failing entry in place and carries on with the
        # rest of the batch rather than faulting the whole request.
        results = []
        for path, args in calls:
            try:
                results.append(self.call(session, path, args))
            except Fault as fault:
                results.append({
                    'isFault': True,
                    'faultCode': fault.faultCode,
                    'faultMessage': fault.faultString,
                })
        return results


class _Handler(SimpleXMLRPCRequestHandler):
    rpc_paths = ('/index.php/api/xmlrpc',)

    def log_message(self, *args):
        pass


@pytest.fixture
def magento_server():
    fake = FakeMagento()
    server = SimpleXMLRPCServer(
        ('127.0.0.1', 0), requestHandler=_Handler, allow_none=True,
        logRequests=False)
    server.register_instance(fake)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    fake.url = 'http://127.0.0.1:%d/' % server.server_address[1]
    try:
        yield fake
    finally:
        server.shutdown()
        server.server_close()
