from robot import TaskManager
from robot import Message
from robot import RoboLogger
from robot import MQTTEngine

from typing import Any
import pytest
import json
from uuid import uuid4
import time
import logging
import asyncio
import os

log = RoboLogger(defaultLevel=logging.DEBUG)


def pytest_addoption(parser):
    parser.addoption("--config_file", action="store")


@pytest.fixture(scope='session')
def config_file(request):
    config_file_value = request.config.option.config_file
    # TEMP FIX FOR VSCODE ISSUE
    return "app/config.json"
    if config_file_value is None:
        print(f'config_file_value = {config_file_value}')
        pytest.skip()
    elif not os.path.exists(config_file_value):
        print(f'config_file_value = {config_file_value}')
        pytest.skip()
    return config_file_value


@pytest.fixture(scope='session')
def mqtt_config(config_file):
    with open(config_file, 'r') as f:
        taskmanConfiguration = json.load(f)
    mqtt_config = taskmanConfiguration['mqtt']
    return mqtt_config


@pytest.fixture(scope='session')
def subscribe_to_topics(mqtt_config):
    return mqtt_config['subscribedTopics']


@pytest.fixture(scope='session')
def taskman(config_file):
    return TaskManager(config_file, asyncio.get_event_loop())


@pytest.fixture(scope='session')
def message() -> Message:
    src_id = uuid4()
    dst_id = uuid4()
    return Message(src_node_id=src_id,
                   dst_node_id=dst_id,
                   body={'testkey': 'testvalue'},
                   topic='testtopic',
                   qos=1)


@pytest.fixture(scope='session')
def event_loop():
    loop = asyncio.get_event_loop()
    log.warning('fixture_event_loop',
                msg=f'event_loop fixture event_loop_id : {id(event_loop)}')
    yield loop
    log.warning('fixture_event_loop',
                msg=f'closing loop!')
    loop.close()


@pytest.fixture(scope='session')
def mqtt_engine(config_file, event_loop):
    with open(config_file, 'r') as f:
        taskmanConfiguration = json.load(f)
    mqtt_config = taskmanConfiguration['mqtt']
    log.warning('fixture_engine', f'event_loop id : {id(event_loop)}')
    ret = MQTTEngine(mqtt_config, event_loop)
    log.info('fixture_engine', f'MQTTEngine id : {id(ret)}')
    return ret


@pytest.fixture(scope='session')
def mqtt_running_engine(mqtt_engine):
    log.info('fixture_running_engine',
             f'running_engine fixture MQTTEngine id : {id(mqtt_engine)}')
    mqtt_engine.run()
    time.sleep(1)
    log.warning('fixture_running_engine',
                f'event_loop id : {id(mqtt_engine._MQTTEngine__event_loop)}')
    return mqtt_engine


class MockImp():
    def __init__(self):
        pass

    def register(self, node_id, in_msg_q: asyncio.Queue):
        return {node_id: in_msg_q}

    @staticmethod
    def get_instance():
        return MockImp()


class MockMQTTEngine():
    def __init__(self):
        self.out_msg_q = MockAsyncioQueryQueue()    # asyncio.Queue

    def subscribe_topic(self, topic, qos):
        return None

    def unsubscribe_topic(self, topic):
        return None

    @staticmethod
    def get_instance():
        return MockMQTTEngine()


class MockAsyncioQueryQueue():
    def __init__(self):
        pass

    @classmethod
    async def put(cls, item: Message):
        cls.message = Message.deserialize(item)

    @classmethod
    async def get(cls):
        return_msg = Message(
            src_node_id=cls.message.dst_node_id,
            dst_node_id=cls.message.src_node_id,
            body={'test_response_message': 'test_response_value'},
            topic=cls.message.topic,
            qos = cls.message.qos
        )
        return return_msg.serialize()
