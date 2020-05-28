from robot import RoboLogger
from robot import MQTTEngine
from robot.common import Singleton

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


def test_MQTTEngine(mqtt_engine, mqtt_config):
    """ Validates that the mqtt_configuration param is of the right type """
    assert mqtt_engine._MQTTEngine__mqtt_configuration == mqtt_config
    log.warning('test_MQTTEngine', f'engine_id = {id(mqtt_engine)}')
    assert isinstance(mqtt_engine.in_msg_q, asyncio.Queue)


def test_MQTTEngine_bad_inputs_type():
    """ Validates that with the wrong type, it can't initialize """
    if MQTTEngine in Singleton._instances:
        del Singleton._instances[MQTTEngine]
    # log.warning('test_MQTTEngine_bad_inputs_type', f'engine_id = {id(eng)}')
    with pytest.raises(TypeError) as excinfo:
        MQTTEngine(mqtt_configuration='bob')
    assert str(excinfo.value) == \
        'mqtt_configuration has to be a dictionnary'


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
def test_MQTTEngine_run(mqtt_running_engine):
    """ validates if the mqtt listener fixture is running """
    assert mqtt_running_engine.is_running
    assert mqtt_running_engine._MQTTEngine__mqtt_client.is_connected()


def test_MQTTEngine_connected_topics(mqtt_running_engine, subscribe_to_topics):
    """ Confirm if subscribed topics are actually subscribed """
    assert set(mqtt_running_engine.subscribed_mqtt_topics) == \
        set(subscribe_to_topics)


def test_MQTTEngine_publish_test(mqtt_running_engine):
    """ Confirm if we can publish a message to a test topic """
    payload = {'test': 'test'}
    msg = mqtt_running_engine._MQTTEngine__mqtt_client.publish(
        topic='test123',
        payload=json.dumps(payload),
        qos=1)
    assert msg.rc == 0


def test_MQTTEngine_on_message_and_dequeue(
        mqtt_running_engine,
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
    assert mqtt_running_engine.in_msg_q.qsize() == \
        len(subscribe_to_topics)
    remaining_topics = deepcopy(subscribe_to_topics)
    i = 0
    # validate that we can dequeue messages with proper payload for all
    # messages pushed on the stack
    while i < len(subscribe_to_topics):
        msg_received_topic, msg_received_payload = \
            mqtt_running_engine.in_msg_q.get_nowait()
        assert msg_received_payload == payload
        assert msg_received_topic in remaining_topics
        remaining_topics.remove(msg_received_topic)
        print(f'tested topic {msg_received_topic}')
        i += 1
    assert mqtt_running_engine.in_msg_q.empty()


def test_MQTTEngine_subscribe_topic(mqtt_running_engine):
    val = mqtt_running_engine.subscribe_topic('test/topic', qos=1)
    assert val == MQTTEngine.SUCCESS


def test_MQTTEngine_unsubscribe_topic(mqtt_running_engine):
    val = mqtt_running_engine.unsubscribe_topic('test/topic')
    assert val == MQTTEngine.SUCCESS


@pytest.mark.asyncio
async def test_MQTTEngine_outbound_message_sender(
        mqtt_running_engine,
        message):
    # await asyncio.sleep(1)
    await mqtt_running_engine.out_msg_q.put(message)
    await asyncio.sleep(1)
    assert mqtt_running_engine.out_msg_q.qsize() == 0
    assert mqtt_running_engine._MQTTEngine__last_outbound_msg_info_rc == \
        MQTT_ERR_SUCCESS


def test_MQTTEngine_graceful_shutdown_bad_input(
        running_engine_test_shutdown,
        event_loop):
    """ Shutdown tests - run at the end """
    with pytest.raises(TypeError) as excinfo:
        event_loop.run_until_complete(
            running_engine_test_shutdown.graceful_shutdown('bob'))
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
