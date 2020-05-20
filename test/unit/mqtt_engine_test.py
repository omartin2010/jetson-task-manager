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
async def listener(config_file, event_loop):
    with open(config_file, 'r') as f:
        taskmanConfiguration = json.load(f)
    mqtt_config = taskmanConfiguration['mqtt']
    return MQTTEngine(mqtt_config, event_loop)


@pytest.fixture(scope='module')
def running_listener(listener):
    listener.run()
    time.sleep(1)
    return listener


def test_MQTTEngine(listener, mqtt_config):
    """ Validates that the mqtt_configuration param is of the right type """
    assert listener.mqtt_configuration == mqtt_config
    assert isinstance(listener.mqtt_message_queue, asyncio.Queue) is True


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


def test_MQTTEngine_run(running_listener):
    """ validates if the mqtt listener fixture is running """
    assert running_listener.running is True


def test_MQTTEngine_connected_topics(running_listener, subscribe_to_topics):
    """ Confirm if subscribed topics are actually subscribed """
    assert set(running_listener.subscribed_mqtt_topics) == \
        set(subscribe_to_topics)


def test_MQTTEngine_publish_test(running_listener):
    """ Confirm if we can publish a message to a test topic """
    payload = {'test': 'test'}
    msg = running_listener.mqttClient.publish(
        topic='test',
        payload=json.dumps(payload),
        qos=1)
    assert msg.rc == 0


def test_MQTTEngine_on_message_and_dequeue(
        running_listener,
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
    assert running_listener.mqtt_message_queue.qsize() == \
        len(subscribe_to_topics)
    remaining_topics = deepcopy(subscribe_to_topics)
    i = 0
    # validate that we can dequeue messages with proper payload for all
    # messages pushed on the stack
    while i < len(subscribe_to_topics):
        msg_received_topic, msg_received_payload = \
            running_listener.mqtt_message_queue.get_nowait()
        assert msg_received_payload == payload
        assert msg_received_topic in remaining_topics
        remaining_topics.remove(msg_received_topic)
        print(f'tested topic {msg_received_topic}')
        i += 1
    assert running_listener.mqtt_message_queue.empty()


def test_MQTTEngine_graceful_shutdown_bad_input(running_listener):
    """ Shutdown tests - run at the end """
    with pytest.raises(TypeError) as excinfo:
        running_listener.graceful_shutdown('bob')
    assert str(excinfo.value) == \
        'input parameter \'s\' has to be a signal'


def test_MQTTEngine_graceful_shutdown_default_params(running_listener):
    """ Shutdown tests - run at the end """
    running_listener.graceful_shutdown()
    time.sleep(1)
    assert running_listener.mqttClient.is_connected() is False


def test_MQTTEngine_graceful_shutdown_good_input(running_listener):
    """ Shutdown tests - run at the end """
    running_listener.graceful_shutdown(signal.SIGINT)
    assert running_listener.mqttClient.is_connected() is False

# ADD TEST FOR NON RESPONSIVE MQTT ENDPOINT --?
