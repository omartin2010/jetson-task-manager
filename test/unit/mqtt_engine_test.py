from robot.logger import RoboLogger
from robot import MQTTEngine
from robot.singleton import Singleton

import pytest
import time
import logging
import json
import signal
import asyncio
import paho.mqtt.client as mqtt
from paho.mqtt.client import MQTT_ERR_SUCCESS
from copy import deepcopy

log = RoboLogger(defaultlevel=logging.DEBUG)


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
def engine(config_file, event_loop):
    with open(config_file, 'r') as f:
        taskmanConfiguration = json.load(f)
    mqtt_config = taskmanConfiguration['mqtt']
    log.warning('fixture_engine', f'event_loop id : {id(event_loop)}')
    ret = MQTTEngine(mqtt_config, event_loop)
    log.info('fixture_engine', f'MQTTEngine id : {id(ret)}')
    return ret


@pytest.fixture(scope='session')
def running_engine(engine):
    log.info('fixture_running_engine',
             f'running_engine fixture MQTTEngine id : {id(engine)}')
    engine.run()
    time.sleep(1)
    log.warning('fixture_running_engine',
                f'event_loop id : {id(engine._MQTTEngine__event_loop)}')
    return engine


@pytest.fixture(scope='function')
def running_engine_test_shutdown(config_file):
    loop = asyncio.get_event_loop()
    log.warning('fixture_running_engine_test_shutdown',
                msg=f'event_loop id : {id(loop)}')
    with open(config_file, 'r') as f:
        taskmanConfiguration = json.load(f)
    mqtt_config = taskmanConfiguration['mqtt']
    if MQTTEngine in Singleton._instances:
        del Singleton._instances[MQTTEngine]
    engine = MQTTEngine(mqtt_config, loop)
    engine.run()
    time.sleep(1)
    return engine


@pytest.mark.test1
def test_MQTTEngine(engine, mqtt_config):
    """ Validates that the mqtt_configuration param is of the right type """
    assert engine._MQTTEngine__mqtt_configuration == mqtt_config
    log.warning('test_MQTTEngine', f'engine_id = {id(engine)}')
    assert isinstance(engine.in_msg_q, asyncio.Queue)


@pytest.mark.test1
def test_MQTTEngine_bad_inputs_type():
    """ Validates that with the wrong type, it can't initialize """
    if MQTTEngine in Singleton._instances:
        del Singleton._instances[MQTTEngine]
    # log.warning('test_MQTTEngine_bad_inputs_type', f'engine_id = {id(eng)}')
    with pytest.raises(TypeError) as excinfo:
        MQTTEngine(mqtt_configuration='bob')
    assert str(excinfo.value) == \
        'mqtt_configuration has to be a dictionnary'


@pytest.mark.test1
def test_MQTTEngine_bad_inputs_keys():
    """ Validate if missing keys in mqtt_config dict """
    if MQTTEngine in Singleton._instances:
        del Singleton._instances[MQTTEngine]
    with pytest.raises(KeyError) as excinfo:
        conf_dict = {
            "brokerIP": 5,
            "brokerPort": 123
        }
        MQTTEngine(conf_dict)
    assert 'Missing some keys in the config dictionnary' in str(excinfo.value)


def test_MQTTEngine_bad_inputs_keys_brokerIP(mqtt_config):
    """ Validates format for some keys of the dict """
    if MQTTEngine in Singleton._instances:
        del Singleton._instances[MQTTEngine]
    with pytest.raises(OSError) as excinfo:
        conf_dict = deepcopy(mqtt_config)
        conf_dict['brokerIP'] = 'abc'
        MQTTEngine(conf_dict)
    assert str(excinfo.value) == \
        'Poorly formatted IP address'


def test_MQTTEngine_bad_inputs_keys_brokerProto(mqtt_config):
    """ Validates format for some keys of the dict """
    if MQTTEngine in Singleton._instances:
        del Singleton._instances[MQTTEngine]
    with pytest.raises(ValueError) as excinfo:
        conf_dict = deepcopy(mqtt_config)
        conf_dict['brokerProto'] = 'abc'
        MQTTEngine(conf_dict)
    assert str(excinfo.value) == \
        'broker proto has to be tcp'


def test_MQTTEngine_bad_inputs_keys_clientID(mqtt_config):
    """ Validates format for some keys of the dict """
    if MQTTEngine in Singleton._instances:
        del Singleton._instances[MQTTEngine]
    with pytest.raises(ValueError) as excinfo:
        conf_dict = deepcopy(mqtt_config)
        conf_dict['clientID'] = 123
        MQTTEngine(conf_dict)
    assert str(excinfo.value) == \
        'clientID has to be a string'


def test_MQTTEngine_bad_inputs_keys_subscribedTopics(mqtt_config):
    """ Validates format for some keys of the dict """
    if MQTTEngine in Singleton._instances:
        del Singleton._instances[MQTTEngine]
    with pytest.raises(ValueError) as excinfo:
        conf_dict = deepcopy(mqtt_config)
        conf_dict['subscribedTopics'] = 123
        MQTTEngine(conf_dict)
    assert str(excinfo.value) == \
        'subscribedTopics has to be a list of strings'


def test_MQTT_Listener_bad_inputs_values_subscribedTopics(mqtt_config):
    """ Validates format for some values of the dict """
    if MQTTEngine in Singleton._instances:
        del Singleton._instances[MQTTEngine]
    with pytest.raises(TypeError) as excinfo:
        conf_dict = deepcopy(mqtt_config)
        conf_dict['subscribedTopics'] = [123]
        MQTTEngine(conf_dict)
    assert 'subscribed topic has to be a string :' in str(excinfo.value)


def test_MQTTEngine_bad_inputs_keys_publishingTopics(mqtt_config):
    """ Validates format for some keys of the dict """
    if MQTTEngine in Singleton._instances:
        del Singleton._instances[MQTTEngine]
    with pytest.raises(ValueError) as excinfo:
        conf_dict = deepcopy(mqtt_config)
        conf_dict['publishingTopics'] = 123
        MQTTEngine(conf_dict)
    assert str(excinfo.value) == \
        'publishingTopics has to be a list of strings'


def test_MQTT_Listener_bad_inputs_values_publishingTopics(mqtt_config):
    """ Validates format for some values of the dict """
    if MQTTEngine in Singleton._instances:
        del Singleton._instances[MQTTEngine]
    with pytest.raises(TypeError) as excinfo:
        conf_dict = deepcopy(mqtt_config)
        conf_dict['publishingTopics'] = [123]
        MQTTEngine(conf_dict)
    assert 'publishing topic has to be a string :' in str(excinfo.value)


# @pytest.mark.asyncio
def test_MQTTEngine_run(running_engine):
    """ validates if the mqtt listener fixture is running """
    assert running_engine.is_running
    assert running_engine._MQTTEngine__mqtt_client.is_connected()


def test_MQTTEngine_connected_topics(running_engine, subscribe_to_topics):
    """ Confirm if subscribed topics are actually subscribed """
    assert set(running_engine.subscribed_mqtt_topics) == \
        set(subscribe_to_topics)


def test_MQTTEngine_publish_test(running_engine):
    """ Confirm if we can publish a message to a test topic """
    payload = {'test': 'test'}
    msg = running_engine._MQTTEngine__mqtt_client.publish(
        topic='test123',
        payload=json.dumps(payload),
        qos=1)
    assert msg.rc == 0


def test_MQTTEngine_on_message_and_dequeue(
        running_engine,
        mqtt_config,
        subscribe_to_topics):
    """
    Tests queuing messages to every queue defined in the config.json
    """
    # Give time for the MQTT client (running_engine) to be up and has
    # subscribed to required topics.
    time.sleep(2)
    client = mqtt.Client(
        client_id='pytest',
        clean_session=True,
        transport='tcp')
    client.connect(
        host=mqtt_config['brokerIP'],
        port=mqtt_config['brokerPort'])
    payload = json.dumps({'test_key': 'test_value'})
    # time.sleep(1)
    for topic in subscribe_to_topics:
        res = client.publish(topic=topic, payload=payload, qos=1)
        print(f'pytest published to mqtt topic {topic}')
        assert res.rc == MQTT_ERR_SUCCESS
    time.sleep(1)
    assert running_engine.in_msg_q.qsize() == \
        len(subscribe_to_topics)
    remaining_topics = deepcopy(subscribe_to_topics)
    i = 0
    # validate that we can dequeue messages with proper payload for all
    # messages pushed on the stack
    while i < len(subscribe_to_topics):
        msg_received_topic, msg_received_payload = \
            running_engine.in_msg_q.get_nowait()
        assert msg_received_payload == payload
        assert msg_received_topic in remaining_topics
        remaining_topics.remove(msg_received_topic)
        print(f'tested topic {msg_received_topic}')
        i += 1
    assert running_engine.in_msg_q.empty()


def test_MQTTEngine_subscribe_topic(running_engine):
    val = running_engine.subscribe_topic('test/topic', qos=1)
    assert val == MQTTEngine.SUCCESS


@pytest.mark.asyncio
async def test_MQTTEngine_graceful_shutdown_bad_input(running_engine):
    """ Shutdown tests - run at the end """
    with pytest.raises(TypeError) as excinfo:
        await running_engine.graceful_shutdown('bob')
    assert str(excinfo.value) == \
        'input parameter \'s\' has to be a signal'


def test_MQTTEngine_graceful_shutdown_default_params(
        running_engine_test_shutdown,
        event_loop):
    """ Shutdown tests - run at the end """
    time.sleep(1)
    event_loop.run_until_complete(
        running_engine_test_shutdown.graceful_shutdown())
    assert not (running_engine_test_shutdown
                ._MQTTEngine__mqtt_client.is_connected())


# @pytest.mark.skip(reason='testing other methods')
def test_MQTTEngine_graceful_shutdown_good_input(
        running_engine_test_shutdown,
        event_loop):
    """ Shutdown tests - run at the end """
    time.sleep(1)
    event_loop.run_until_complete(
        running_engine_test_shutdown.graceful_shutdown(signal.SIGINT))
    assert not (running_engine_test_shutdown
                ._MQTTEngine__mqtt_client.is_connected())




# ADD TEST FOR NON RESPONSIVE MQTT ENDPOINT --?
# need to add tests for outbound_message_processorr
# need to add tests for subsribe and unsubscribe topics
