from robot import RoboLogger
from robot import QueryProcessor
from robot import Message
import robot.taskman.query_proc
from conftest import MockImp, MockMQTTEngine, MockAsyncioQueryQueue

import pytest
# import asyncio
import logging
import uuid
from _pytest.monkeypatch import monkeysession

log = RoboLogger(defaultLevel=logging.DEBUG)


@pytest.fixture(scope='session')
def query_proc(mqtt_config, event_loop, monkeysession):
    """ mqtt_config is there to get the singleton in the QP
    constructor
    """
    def ret_none():
        return None

    monkeysession.setattr(
        robot.taskman.query_proc,
        'InboundMessageProcessor',
        MockImp)
    monkeysession.setattr(
        robot.taskman.query_proc,
        'MQTTEngine',
        MockMQTTEngine)
    monkeysession.setattr(
        robot.taskman.query_proc.asyncio,
        'Queue',
        MockAsyncioQueryQueue
    )
    qp = QueryProcessor()
    return qp


@pytest.fixture(scope='session')
def message_params():
    src_node_id = uuid.uuid4()
    dst_node_id = uuid.uuid4()
    body = {'testkey1': 'testvalue1',
            'testkey2': 'testvalue2'}
    topic = 'test_topic'
    qos = 1
    return (src_node_id,
            dst_node_id,
            body,
            topic,
            qos)


def test_QueryProcessor(query_proc):
    """ will only fail if exception in the __init__
    """
    assert True


@pytest.mark.asyncio
async def test_Query(query_proc, message: Message):

    # Simulate a listener on that topic
    # Put a message on the queue and publish to it
    resp = await query_proc.query(message)    # type: Message

    # Validate that we are retrieving the response
    assert resp.src_node_id == message.dst_node_id
    assert resp.dst_node_id == message.src_node_id
    assert resp.qos == message.qos
    assert list(resp.body.keys()) == ['test_response_message']
    assert list(resp.body.values()) == ['test_response_value']
    assert resp.topic == message.topic
