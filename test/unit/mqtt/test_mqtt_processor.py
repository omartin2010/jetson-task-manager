import pytest
from robot import MQTTProcessor
import queue
import asyncio
import time


@pytest.fixture(scope='module')
def processor():
    msg_queue = queue.Queue()
    loop = asyncio.get_event_loop()
    return MQTTProcessor(msg_queue, loop)


@pytest.fixture(scope='module')
def running_processor(processor):
    processor.run()
    time.sleep(1)
    return processor


@pytest.fixture()
def filled_message_queue(subscribe_to_topics):
    msg_queue = queue.Queue()
    for topic in subscribe_to_topics:
        data = {
            'test_key': 'test_value'
        }
        msg_queue.put(topic, data)
    return msg_queue


def test_MQTTProcessor_bad_inputs_message_queue():
    with pytest.raises(TypeError) as excinfo:
        MQTTProcessor('bob', None)
    assert str(excinfo.value) == \
        'Constructor requires mqtt_message_queue to be of queue.Queue() class'


def test_MQTTProcessor_bad_inputs_event_loop():
    with pytest.raises(TypeError) as excinfo:
        MQTTProcessor(queue.Queue(), 'bob')
    assert str(excinfo.value) == \
        (f'Constructor requires event_loop to be of '
         f'asyncio.BaseEventLoop() class')


def test_MQTTProcessor_process_message(
        filled_message_queue,
        running_processor):
    """
    Description : tests a running queue to ensure messages in the queue are
        processed
    """
    running_processor.mqtt_message_queue = filled_message_queue
    start_time = time.time()
    timeout = False
    while not running_processor.mqtt_message_queue.empty() and not timeout:
        duration = time.time() - start_time
        timeout = True if duration > 10 else False
    assert timeout is False
