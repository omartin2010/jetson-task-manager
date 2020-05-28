import asyncio
import pytest
# from robot import MQTTProcessor
import time
# from pytest_mock import mocker


@pytest.fixture(scope='module')
def processor(taskman):
    msg_queue = asyncio.Queue()
    loop = asyncio.get_event_loop()
    return MQTTProcessor(msg_queue, loop, taskman)


@pytest.fixture(scope='module')
def running_processor(processor):
    processor.run()
    time.sleep(1)
    return processor


@pytest.fixture
def create_mock_coro(mocker, monkeypatch):
    def _create_mock_patch_coro(to_patch=None):
        mock = mocker.Mock()

        async def _coro(*args, **kwargs):
            return mock(*args, **kwargs)

        if to_patch:  # <-- may not need/want to patch anything
            monkeypatch.setattr(to_patch, _coro)
        return mock, _coro

    return _create_mock_patch_coro


@pytest.fixture
async def filled_message_queue():
    msg_queue = asyncio.Queue()
    message_list = []
    message_list.append(('robot/taskman/kill_switch', ''))
    # message_list.append(('robot/taskman/configure', {'testkey': 'testvalue'}))
    # message_list.append(('robot/taskman/logger/multiple',
    #                     {'mqtt_processor_process_messages': 10,
    #                      'mqtt_processor_run': 10}))
    # message_list.append(('robot/taskman/logger',
    #                     {'logger': 'mqtt_processor_run', 'level': 10}))
    for topic, payload in message_list:
        await msg_queue.put((topic, payload))
    return msg_queue


def test_MQTTProcessor_bad_inputs_message_queue():
    with pytest.raises(TypeError) as excinfo:
        MQTTProcessor('bob', None, None)
    assert str(excinfo.value) == \
        (f'Constructor requires mqtt_message_queue '
         f'to be of asyncio.Queue() class')


def test_MQTTProcessor_bad_inputs_event_loop():
    with pytest.raises(TypeError) as excinfo:
        MQTTProcessor(asyncio.Queue(), 'bob', None)
    assert str(excinfo.value) == \
        (f'Constructor requires event_loop to be of '
         f'asyncio.BaseEventLoop() class')


def test_MQTTProcessor_bad_inputs_taskman():
    with pytest.raises(TypeError) as excinfo:
        MQTTProcessor(asyncio.Queue(), asyncio.get_event_loop(), None)
    assert str(excinfo.value) == \
        (f'Constructor requires taskman to be of '
         f'TaskManager() class')


@pytest.mark.asyncio
async def test_MQTTProcessor_process_message(
        filled_message_queue,
        processor):
    """
    Description : tests a running queue to ensure messages in the queue are
        processed
    """
    processor.mqtt_message_queue = filled_message_queue
    assert not processor.mqtt_message_queue.empty()
    await processor.process_messages(timeout=120)
    assert processor.mqtt_message_queue.empty()
