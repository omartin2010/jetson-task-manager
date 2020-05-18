import pytest
import json
from robot import TaskManager
import asyncio
import os


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


@pytest.fixture(scope='module')
def mqtt_config(config_file):
    with open(config_file, 'r') as f:
        taskmanConfiguration = json.load(f)
    mqtt_config = taskmanConfiguration['mqtt']
    return mqtt_config


@pytest.fixture(scope='module')
def subscribe_to_topics(mqtt_config):
    return mqtt_config['subscribedTopics']


@pytest.fixture(scope='module')
def taskman(config_file):
    return TaskManager(config_file, asyncio.get_event_loop())
