# from test.conftest import event_loop, mqtt_config
from robot import RoboLogger, Message
from robot import InboundMessageProcessor
from conftest import MockImp, MockMQTTEngine, MockAsyncioQueryQueue

import pytest
import logging
import uuid
from _pytest.monkeypatch import monkeysession

log = RoboLogger(defaultLevel=logging.DEBUG)


@pytest.fixture(scope='session')
def imp(mqtt_config, event_loop):
    imp = InboundMessageProcessor(event_loop, mqtt_config)
    return imp


def test_InboundMessageProcesor(imp):
    assert True
