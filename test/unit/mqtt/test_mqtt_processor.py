import pytest
from robot import MQTTProcessor
import threading
import asyncio
import time


@pytest.fixture(scope='module')
def processor():
    msg_queue = asyncio.Queue()
    loop = asyncio.get_event_loop()
    return MQTTProcessor(msg_queue, loop)


@pytest.fixture(scope='module')
def running_processor(processor):
    # thread = threading.Thread(
    #     target=func(processor),
    #     name='mocked_eventloop')
    # thread.start()
    # print('thread started...')
    processor.run()
    time.sleep(1)
    return processor


@pytest.fixture()
def filled_message_queue(subscribe_to_topics):
    msg_queue = asyncio.Queue()
    for topic in subscribe_to_topics:
        data = {
            'test_key': 'test_value'
        }
        msg_queue.put((topic, data))
    return msg_queue


def test_MQTTProcessor_bad_inputs_message_queue():
    with pytest.raises(TypeError) as excinfo:
        MQTTProcessor('bob', None)
    assert str(excinfo.value) == \
        'Constructor requires mqtt_message_queue to be of queue.Queue() class'


def test_MQTTProcessor_bad_inputs_event_loop():
    with pytest.raises(TypeError) as excinfo:
        MQTTProcessor(asyncio.Queue(), 'bob')
    assert str(excinfo.value) == \
        (f'Constructor requires event_loop to be of '
         f'asyncio.BaseEventLoop() class')


@pytest.mark.asyncio
async def test_MQTTProcessor_process_message(
        filled_message_queue,
        running_processor):
    """
    Description : tests a running queue to ensure messages in the queue are
        processed
    """
    # Mock the message queue
    running_processor.mqtt_message_queue = filled_message_queue
    start_time = time.time()
    timeout = False
    await running_processor.process_messages()
    assert running_processor.mqtt_message_queue.empty()
