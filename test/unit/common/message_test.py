from robot import RoboLogger
from robot import Message

import pytest
import logging
import uuid
from copy import deepcopy

log = RoboLogger(defaultLevel=logging.DEBUG)


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


@pytest.fixture(scope='session')
def message(message_params):
    src_node_id, dst_node_id, body, topic, qos = message_params
    msg = Message(src_node_id=src_node_id,
                  dst_node_id=dst_node_id,
                  body=body,
                  topic=topic,
                  qos=qos)
    return msg


def test_Message_bad_input_src_node_id(message_params):
    src_node_id, dst_node_id, body, topic, qos = message_params
    with pytest.raises(TypeError) as excinfo:
        Message(src_node_id='test',
                dst_node_id=dst_node_id,
                body=body,
                topic=topic,
                qos=qos)
    assert str(excinfo.value) == \
        'src_id has to be a UUID'


def test_Message_bad_input_dst_node_id(message_params):
    src_node_id, dst_node_id, body, topic, qos = message_params
    with pytest.raises(TypeError) as excinfo:
        Message(src_node_id=src_node_id,
                dst_node_id='test',
                body=body,
                topic=topic,
                qos=qos)
    assert str(excinfo.value) == \
        'dst_id has to be a UUID'


def test_Message_bad_input_body(message_params):
    src_node_id, dst_node_id, body, topic, qos = message_params
    with pytest.raises(TypeError) as excinfo:
        Message(src_node_id=src_node_id,
                dst_node_id=dst_node_id,
                body='test',
                topic=topic,
                qos=qos)
    assert str(excinfo.value) == \
        'body has to be a dict'


def test_Message_bad_input_topic(message_params):
    src_node_id, dst_node_id, body, topic, qos = message_params
    with pytest.raises(TypeError) as excinfo:
        Message(src_node_id=src_node_id,
                dst_node_id=dst_node_id,
                body=body,
                topic=123,
                qos=qos)
    assert str(excinfo.value) == \
        'topic has to be a str'


def test_Message_bad_input_qos(message_params):
    src_node_id, dst_node_id, body, topic, qos = message_params
    with pytest.raises(ValueError) as excinfo:
        Message(src_node_id=src_node_id,
                dst_node_id=dst_node_id,
                body=body,
                topic=topic,
                qos=4)
    assert str(excinfo.value) == \
        'QOS has to be 0, 1 or 2'


def test_Message(message_params):
    src_node_id, dst_node_id, body, topic, qos = message_params
    msg = Message(src_node_id=src_node_id,
                  dst_node_id=dst_node_id,
                  body=body,
                  topic=topic,
                  qos=qos)
    assert isinstance(msg, Message)


def test_Message_eq(message):
    msg2 = deepcopy(message)
    assert message == msg2
    msg2.body = 'hello'
    assert not message == msg2


def test_Message_serialize_deserialize(message):
    ser_msg = message.serialize()
    unser_msg = Message.deserialize(ser_msg)
    assert message == unser_msg
