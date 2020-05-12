import pytest
import time
import json
import signal
from robot import MQTTListener
import paho.mqtt.client as mqtt
import queue
from copy import deepcopy


@pytest.fixture(scope='module')
def listener(config_file):
    with open(config_file, 'r') as f:
        taskmanConfiguration = json.load(f)
    mqtt_config = taskmanConfiguration['mqtt']
    return MQTTListener(mqtt_config)


@pytest.fixture(scope='module')
def running_listener(listener):
    listener.run()
    time.sleep(1)
    return listener


def test_MQTTListener(listener, mqtt_config):
    assert listener.mqtt_configuration == mqtt_config
    assert isinstance(listener.mqtt_message_queue, queue.Queue) is True


def test_MQTTListener_bad_inputs_type(mqtt_config):
    with pytest.raises(TypeError) as excinfo:
        MQTTListener(mqtt_configuration='bob')
    assert str(excinfo.value) == \
        'mqtt_configuration has to be a dictionnary'


def test_MQTTListener_bad_inputs_keys(mqtt_config):
    with pytest.raises(KeyError) as excinfo:
        conf_dict = {
            "brokerIP": 5,
            "brokerPort": 123
        }
        MQTTListener(conf_dict)
    assert 'Missing some keys in the config dictionnary' in str(excinfo.value)


def test_MQTTListener_bad_inputs_keys_brokerIP(mqtt_config):
    with pytest.raises(OSError) as excinfo:
        conf_dict = deepcopy(mqtt_config)
        conf_dict['brokerIP'] = 'abc'
        MQTTListener(conf_dict)
    assert str(excinfo.value) == \
        'Poorly formatted IP address'


def test_MQTTListener_bad_inputs_keys_brokerProto(mqtt_config):
    with pytest.raises(ValueError) as excinfo:
        conf_dict = deepcopy(mqtt_config)
        conf_dict['brokerProto'] = 'abc'
        MQTTListener(conf_dict)
    assert str(excinfo.value) == \
        'broker proto has to be tcp'


def test_MQTTListener_bad_inputs_keys_clientID(mqtt_config):
    with pytest.raises(ValueError) as excinfo:
        conf_dict = deepcopy(mqtt_config)
        conf_dict['clientID'] = 123
        MQTTListener(conf_dict)
    assert str(excinfo.value) == \
        'clientID has to be a string'


def test_MQTTListener_bad_inputs_keys_subscribedTopics(mqtt_config):
    with pytest.raises(ValueError) as excinfo:
        conf_dict = deepcopy(mqtt_config)
        conf_dict['subscribedTopics'] = 123
        MQTTListener(conf_dict)
    assert str(excinfo.value) == \
        'subscribedTopics has to be a list of strings'


def test_MQTT_Listener_bad_inputs_values_subscribedTopics(mqtt_config):
    with pytest.raises(TypeError) as excinfo:
        conf_dict = deepcopy(mqtt_config)
        conf_dict['subscribedTopics'] = [123]
        MQTTListener(conf_dict)
    assert 'subscribed topic has to be a string :' in str(excinfo.value)


def test_MQTTListener_bad_inputs_keys_publishingTopics(mqtt_config):
    with pytest.raises(ValueError) as excinfo:
        conf_dict = deepcopy(mqtt_config)
        conf_dict['publishingTopics'] = 123
        MQTTListener(conf_dict)
    assert str(excinfo.value) == \
        'publishingTopics has to be a list of strings'


def test_MQTT_Listener_bad_inputs_values_publishingTopics(mqtt_config):
    with pytest.raises(TypeError) as excinfo:
        conf_dict = deepcopy(mqtt_config)
        conf_dict['publishingTopics'] = [123]
        MQTTListener(conf_dict)
    assert 'publishing topic has to be a string :' in str(excinfo.value)


def test_MQTTListener_run(running_listener):
    # validate if variable confirms it
    assert running_listener.running is True


def test_MQTTListener_connected_topics(
        running_listener,
        subscribe_to_topics):
    # Confirm if subscribed topics are actually subscribed
    assert set(running_listener.subscribed_mqtt_topics) == \
        set(subscribe_to_topics)


def test_MQTTListener_publish_test(
        running_listener):
    # Confirm if we can publish a message to a test topic
    payload = {'test': 'test'}
    msg = running_listener.mqttClient.publish(
        topic='test',
        payload=json.dumps(payload),
        qos=1)
    assert msg.rc == 0


def test_MQTTListener_on_message_and_dequeue(
        running_listener,
        mqtt_config,
        subscribe_to_topics):
    """
    Description:
        Tests queuing messages to MQTT and ensuring they are in the queue
            for further processing.
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
    while i < len(subscribe_to_topics):
        msg_received_topic, msg_received_payload = \
            running_listener.mqtt_message_queue.get()
        assert msg_received_payload == payload
        assert msg_received_topic in remaining_topics
        remaining_topics.remove(msg_received_topic)
        print(f'tested topic {msg_received_topic}')
        i += 1
    assert running_listener.mqtt_message_queue.empty()


def test_MQTTListener_graceful_shutdown_bad_input(running_listener):
    with pytest.raises(TypeError) as excinfo:
        running_listener.graceful_shutdown('bob')
    assert str(excinfo.value) == \
        'input parameter \'s\' has to be a signal'


def test_MQTTListener_graceful_shutdown_default_params(running_listener):
    running_listener.graceful_shutdown()
    time.sleep(1)
    assert running_listener.mqttClient.is_connected() is False


def test_MQTTListener_graceful_shutdown_good_input(running_listener):
    running_listener.graceful_shutdown(signal.SIGINT)
    assert running_listener.mqttClient.is_connected() is False






##### ADD TEST FOR NON RESPONSIVE MQTT ENDPOINT