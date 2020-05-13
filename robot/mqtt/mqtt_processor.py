import asyncio
import traceback
from ..logger import RoboLogger
log = RoboLogger.getLogger()


class MQTTProcessor(object):
    """
    Description :
        Class used to process MQTT messages for the robot
    """
    # Defines constants for this class
    __LOG_MQTTPROCESSOR_PROCESS_MESSAGES = 'mqtt_processor_process_messages'
    __LOG_MQTTPROCESSOR_RUN = 'mqtt_processor_run'

    def __init__(
            self,
            mqtt_message_queue: asyncio.Queue,
            event_loop: asyncio.BaseEventLoop) -> None:
        """
        Args:
            mqtt_message_queue: queue, receives messages queued from the mqtt
                listener
            event_loop : event loop on which to run the process_message task
        """
        if not isinstance(mqtt_message_queue, asyncio.Queue):
            raise TypeError(f'Constructor requires mqtt_message_queue to '
                            f'be of queue.Queue() class')
        if not isinstance(event_loop, asyncio.BaseEventLoop):
            raise TypeError(f'Constructor requires event_loop to be of '
                            f'asyncio.BaseEventLoop() class')
        self.mqtt_message_queue = mqtt_message_queue
        self.event_loop = event_loop
        self.is_running = False

    def run(self):
        """
        Description
            Launches the runner (asyncio loop) for the processor.
        """
        try:
            self.event_loop.create_task(
                self.process_messages())
            self.is_running = True
            # if not self.event_loop.is_running():
            #     log.warning(self.__LOG_MQTTPROCESSOR_RUN,
            #                 f'Event loop not running')
            #     raise Exception(f'Event loop not running!')
        except:
            raise

    async def process_messages(
            self):
        """
        Description : This function receives the messages from MQTT to the
            task manager.
        Args:
            loopDelay: float, delay to sleep at the end of the loop
        """
        log.warning(self.__LOG_MQTTPROCESSOR_PROCESS_MESSAGES,
                    msg='Launching MQTT processing async task')
        try:
            if not self.event_loop.is_running():
                log.warning(self.__LOG_MQTTPROCESSOR_RUN,
                            f'Event loop not running')
                raise Exception(f'Event loop not running!')
            while self.is_running:
                # until there is something
                topic, msgdict = await self.mqtt_message_queue.get()
                # Check if need to shut down
                if topic == 'bot/kill_switch':
                    log.warning(
                        self.__LOG_MQTTPROCESSOR_PROCESS_MESSAGES,
                        msg='Kill switch activated')
                    self.kill_switch()
                elif topic == 'bot/taskman/configure':
                    log.info(
                        self.__LOG_MQTTPROCESSOR_PROCESS_MESSAGES,
                        msg=f'Modifying configuration item...')
                    for k, v in msgdict.items():
                        if k in dir(self):
                            log.info(
                                self.__LOG_MQTTPROCESSOR_PROCESS_MESSAGES,
                                msg=f'Setting attribute self.{k} '
                                    f'to value {v}')
                            # Adding / changing configuration
                            # parameters for the object
                            self.__setattr__(k, v)
                            log.warning(
                                self.__LOG_MQTTPROCESSOR_PROCESS_MESSAGES,
                                msg=f'After validation, '
                                    f'attribute self.{k} '
                                    f'= "{self.__getattribute__(k)}"')
                        else:
                            log.error(
                                self.__LOG_MQTTPROCESSOR_PROCESS_MESSAGES,
                                msg=f'Attribute self.{k} not '
                                    f'found. Will not add it.')
                elif topic == 'bot/taskman/logger':
                    # Changing the logging level on the fly...
                    log.setLevel(
                        msgdict['logger'],
                        lvl=msgdict['level'])
                elif topic == 'bot/taskman/multiple':
                    # Changing the logging level on the fly for
                    # multiple loggers at a time
                    for logger, level in msgdict.items():
                        log.setLevel(logger, level)
                else:
                    raise NotImplementedError
        except NotImplementedError:
            log.warning(self.__LOG_MQTTPROCESSOR_PROCESS_MESSAGES,
                        msg=f'MQTT topic not implemented.')
        except asyncio.futures.CancelledError:
            log.warning(self.__LOG_MQTTPROCESSOR_PROCESS_MESSAGES,
                        msg=f'Cancelled the MQTT dequeing task.')
        except Exception:
            log.error(self.__LOG_MQTTPROCESSOR_PROCESS_MESSAGES,
                      msg=f'Error: {traceback.print_exc()}')
            raise
        finally:
            log.warning(self.__LOG_MQTTPROCESSOR_PROCESS_MESSAGES,
                        msg=f'Exiting the process_message corouting.')
