import pytest
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
