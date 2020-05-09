# flake8: ignore=E501
from logger import RoboLogger
import constant as ct
from taskman import TaskManager
import asyncio
import os
import sys
import argparse
import logging
import json
import traceback
import signal


log = RoboLogger.getLogger()
log.warning(ct.LOG_STARTUP,
            msg="Initial imports are completed.")


def main():
    """
    Full Jetson Detector Program
    """

    parser = argparse.ArgumentParser(description="Task Manager Program")
    parser.add_argument(
        '--config_file',
        help=f'json configuration file containint params '
             f'to initialize the task manager',
        type=str)
    args = parser.parse_args()

    try:
        global taskManager
        if not os.path.exists(args.config_file):
            raise ValueError(
                f'Cannot find configuration file "{args.config_file}"')
        with open(args.config_file, 'r') as f:
            taskmanConfiguration = json.load(f)

        log.warning(ct.LOG_STARTUP_MAIN,
                    msg='Launching task manager now.')
        loop = asyncio.get_event_loop()
        loop.set_exception_handler(handle_exception)
        log.warning(ct.LOGGER_OBJECT_DETECTOR_STARTUP,
                    msg='Launching runner.')
        signals = (signal.SIGINT, signal.SIGTERM)
        for s in signals:
            loop.add_signal_handler(s, lambda s=s: loop.create_task(
                taskManager.graceful_shutdown(s)))
        taskManager = TaskManager(taskmanConfiguration, loop)
        loop.create_task(taskManager.run())
        loop.run_forever()

    except SystemExit:
        log.info(ct.LOG_STARTUP_MAIN, 'Caught SystemExit...')
    except Exception:
        log.critical(ct.LOG_STARTUP_MAIN,
                     'System Crash : {}'.format(traceback.print_exc()))
    finally:
        loop.close()
        logging.shutdown()


def handle_exception(loop, context):
    msg = context.get("exception", context["message"])
    log.error(ct.LOG_STARTUP_HANDLE_EXC,
              f'Caught exception: {msg}')
    log.critical(ct.LOG_STARTUP_HANDLE_EXC,
                 f'Calling graceful_shutdown from exception handler.')
    loop.create_task(taskManager.graceful_shutdown())


if __name__ == "__main__":
    main()
    log.info(ct.LOG_STARTUP_MAIN, "Done")
    try:
        sys.exit(0)
    except SystemExit:
        log.info(ct.LOG_STARTUP_MAIN, 'Exiting startup.')
