from robot import RoboLogger
from robot import QueryProcessor
from robot import InboundMessageProcessor

import pytest
import logging
import uuid
# from collections import deque

log = RoboLogger(defaultLevel=logging.DEBUG)


@pytest.fixture(scope='session')
def query_proc(mqtt_config, event_loop):
    """ mqtt_config is there to get the singleton in the QP
    constructor
    """
    imp = InboundMessageProcessor(event_loop, mqtt_config)
    qp = QueryProcessor()
    # qp = QueryProcessor(deque())
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
async def test_Query(query_proc, message):

    # Simulate a listener on that topic
    # Put a message on the queue and publish to it
    await query_proc.query(message)

    # Respond to the query

    # Validate that we are retrieving the response
    await query_proc.out_msg_q.put(message.serialize())
    assert True
