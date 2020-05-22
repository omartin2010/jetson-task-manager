import pytest
import time
import json
import signal
import asyncio
from robot import MQTTEngine
import paho.mqtt.client as mqtt
from copy import deepcopy


@pytest.fixture(scope='function')
@pytest.mark.asyncio
async def engine(config_file, event_loop):
    with open(config_file, 'r') as f:
        taskmanConfiguration = json.load(f)
    mqtt_config = taskmanConfiguration['mqtt']
    print(f'in test : {id(event_loop)}')
    return MQTTEngine(mqtt_config, event_loop)


@pytest.fixture(scope='function')
@pytest.mark.asyncio
async def running_engine(engine):
    engine.run()
    await asyncio.sleep(1)  # time.sleep(1)
    return engine


def test_MQTTEngine(engine, mqtt_config):
    """ Validates that the mqtt_configuration param is of the right type """
    assert engine._MQTTEngine__mqtt_configuration == mqtt_config
    assert isinstance(engine.in_msg_q, asyncio.Queue)


def test_MQTTEngine_bad_inputs_type(mqtt_config):
    """ Validates that with the wrong type, it can't initialize """
    with pytest.raises(TypeError) as excinfo:
        MQTTEngine(mqtt_configuration='bob')
    assert str(excinfo.value) == \
        'mqtt_configuration has to be a dictionnary'


def test_MQTTEngine_bad_inputs_keys(mqtt_config):
    """ Validate if missing keys in mqtt_config dict """
    with pytest.raises(KeyError) as excinfo:
        conf_dict = {
            "brokerIP": 5,
            "brokerPort": 123
        }
        MQTTEngine(conf_dict)
    assert 'Missing some keys in the config dictionnary' in str(excinfo.value)


def test_MQTTEngine_bad_inputs_keys_brokerIP(mqtt_config):
    """ Validates format for some keys of the dict """
    with pytest.raises(OSError) as excinfo:
        conf_dict = deepcopy(mqtt_config)
        conf_dict['brokerIP'] = 'abc'
        MQTTEngine(conf_dict)
    assert str(excinfo.value) == \
        'Poorly formatted IP address'


def test_MQTTEngine_bad_inputs_keys_brokerProto(mqtt_config):
    """ Validates format for some keys of the dict """
    with pytest.raises(ValueError) as excinfo:
        conf_dict = deepcopy(mqtt_config)
        conf_dict['brokerProto'] = 'abc'
        MQTTEngine(conf_dict)
    assert str(excinfo.value) == \
        'broker proto has to be tcp'


def test_MQTTEngine_bad_inputs_keys_clientID(mqtt_config):
    """ Validates format for some keys of the dict """
    with pytest.raises(ValueError) as excinfo:
        conf_dict = deepcopy(mqtt_config)
        conf_dict['clientID'] = 123
        MQTTEngine(conf_dict)
    assert str(excinfo.value) == \
        'clientID has to be a string'


def test_MQTTEngine_bad_inputs_keys_subscribedTopics(mqtt_config):
    """ Validates format for some keys of the dict """
    with pytest.raises(ValueError) as excinfo:
        conf_dict = deepcopy(mqtt_config)
        conf_dict['subscribedTopics'] = 123
        MQTTEngine(conf_dict)
    assert str(excinfo.value) == \
        'subscribedTopics has to be a list of strings'


def test_MQTT_Listener_bad_inputs_values_subscribedTopics(mqtt_config):
    """ Validates format for some values of the dict """
    with pytest.raises(TypeError) as excinfo:
        conf_dict = deepcopy(mqtt_config)
        conf_dict['subscribedTopics'] = [123]
        MQTTEngine(conf_dict)
    assert 'subscribed topic has to be a string :' in str(excinfo.value)


def test_MQTTEngine_bad_inputs_keys_publishingTopics(mqtt_config):
    """ Validates format for some keys of the dict """
    with pytest.raises(ValueError) as excinfo:
        conf_dict = deepcopy(mqtt_config)
        conf_dict['publishingTopics'] = 123
        MQTTEngine(conf_dict)
    assert str(excinfo.value) == \
        'publishingTopics has to be a list of strings'


def test_MQTT_Listener_bad_inputs_values_publishingTopics(mqtt_config):
    """ Validates format for some values of the dict """
    with pytest.raises(TypeError) as excinfo:
        conf_dict = deepcopy(mqtt_config)
        conf_dict['publishingTopics'] = [123]
        MQTTEngine(conf_dict)
    assert 'publishing topic has to be a string :' in str(excinfo.value)


@pytest.mark.asyncio
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
    client = mqtt.Client(
        client_id='pytest',
        clean_session=True,
        transport='tcp')
    client.connect(
        host=mqtt_config['brokerIP'],
        port=mqtt_config['brokerPort'])
    payload = json.dumps({'test_key': 'test_value'})
    for topic in subscribe_to_topics:
        client.publish(topic=topic, payload=payload, qos=1)
        time.sleep(0.5)
    time.sleep(2)
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


def test_MQTTEngine_graceful_shutdown_bad_input(running_engine):
    """ Shutdown tests - run at the end """
    with pytest.raises(TypeError) as excinfo:
        running_engine.graceful_shutdown('bob')
    assert str(excinfo.value) == \
        'input parameter \'s\' has to be a signal'


def test_MQTTEngine_graceful_shutdown_default_params(running_engine):
    """ Shutdown tests - run at the end """
    time.sleep(10)
    running_engine.graceful_shutdown()
    assert not running_engine._MQTTEngine__mqtt_client.is_connected()


def test_MQTTEngine_graceful_shutdown_good_input(running_engine):
    """ Shutdown tests - run at the end """
    time.sleep(10)
    running_engine.graceful_shutdown(signal.SIGINT)
    assert not running_engine._MQTTEngine__mqtt_client.is_connected()


def test_MQTTEngine_subscribe_topic(running_engine):
    val = running_engine.subscribe_topic('test/topic', qos=1)
    assert val == MQTTEngine.SUCCESS


# ADD TEST FOR NON RESPONSIVE MQTT ENDPOINT --?
# need to add tests for outbound_message_processorr
# need to add tests for subsribe and unsubscribe topics
