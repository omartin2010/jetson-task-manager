# Modules from current package
from logger import RoboLogger

# Other imports
import json
import queue
import traceback
import threading
import paho.mqtt.client as mqtt
import asyncio
log = RoboLogger.getLogger()


class TaskManager(object):
    """ Main class for the task manager running on the jetson """

    # Defines constants for this class
    __LOG_TASKMAN_MAIN = 'taskman_main'
    __LOG_TASKMAN_GRACEFUL_SHUTDOWN = 'taskman_graceful_shutdown'
    __LOG_TASKMAN_KILL_SWITCH = 'taskman_kill_switch'
    __LOG_TASKMAN_ASYNC_RUN = 'taskman_async_run'
    __LOG_TASKMAN_ASYNC_WATCHDOG = 'taskman_async_watchdog'
    __LOG_TASKMAN_EVENT_LOOP_START_MAIN_TASKS = \
        'taskman_event_loop_start_main_tasks'
    __LOG_TASKMAN_ASYNC_PROCESS_MQTT_MESSAGES = \
        'taskman_async_process_mqtt_messages'
    __LOG_TASKMAN_THREAD_MQTT_LISTENER = 'taskman_thread_mqtt_listener'

    def __init__(
            self,
            configuration: dict,
            loop: asyncio.AbstractEventLoop) -> None:
        self.configuration = configuration
        self.mqtt_message_queue = queue.Queue()
        self.thread_exception_queue = queue.Queue()
        self.started_threads = {}
        self.eventLoop = loop

    async def graceful_shutdown(
            self,
            s=None) -> None:
        """
        Description : Ensures a clean shutdown of the robot, including
            shutting down the Kinect camera
        Args:
            signal = signal from the signal library. Could be SIGINT, SIGTERM,
                etc. if set to None, it's cancelled from another process.
        """
        try:
            if s is not None:
                log.critical(self.__LOG_TASKMAN_GRACEFUL_SHUTDOWN,
                             msg=f'Initiating graceful shutdown now '
                                 f'from received signal {s.name}.')
            else:
                log.critical(self.__LOG_TASKMAN_GRACEFUL_SHUTDOWN,
                             msg=f'Initiating graceful shutdown now '
                                 f'from non signal.')
            # region asyncio event loop tasks
            try:
                tasks = [t for t in asyncio.Task.all_tasks(loop=self.eventLoop)
                         if t is not asyncio.Task.current_task()]
                log.info(self.__LOG_TASKMAN_GRACEFUL_SHUTDOWN,
                         msg=f'Cancelling task {len(tasks)} tasks...')
                [task.cancel() for task in tasks]
                log.info(self.__LOG_TASKMAN_GRACEFUL_SHUTDOWN,
                         msg=f'Gaterhing out put of cancellation '
                             f'of {len(tasks)} tasks...')
                out_list = await asyncio.gather(
                    *tasks,
                    loop=self.eventLoop,
                    return_exceptions=True)
                for idx, out in enumerate(out_list):
                    if isinstance(out, Exception):
                        log.error(self.__LOG_TASKMAN_GRACEFUL_SHUTDOWN,
                                  msg=f'Exception in stopping task {idx}')
                log.warning(self.__LOG_TASKMAN_GRACEFUL_SHUTDOWN,
                            msg=f'Done cancelling tasks.')
            except:
                pass
            # endregion asyncio event loop tasks

            # Stop MQTT client:
            try:
                self.mqttClient.loop_stop()
                self.mqttClient.disconnect()
                if self.mqttClient.is_connected():
                    log.error(self.__LOG_TASKMAN_GRACEFUL_SHUTDOWN,
                              msg=f'Unable to stop MQTT client.')
                else:
                    log.info(self.__LOG_TASKMAN_GRACEFUL_SHUTDOWN,
                             msg=f'Stopped MQTT client.')
            except:
                log.error(self.__LOG_TASKMAN_GRACEFUL_SHUTDOWN,
                          msg=f'Exception in shutting down MQTT')

            try:
                # Stop remaining threads
                for thread, event in self.started_threads.items():
                    if thread.is_alive():
                        event.set()
                        await asyncio.sleep(0.5)
                        if thread.is_alive():
                            log.error(self.__LOG_TASKMAN_GRACEFUL_SHUTDOWN,
                                      msg=f'Problem shutting down '
                                          f'some threads!')
            except:
                log.error(self.__LOG_TASKMAN_GRACEFUL_SHUTDOWN,
                          msg=f'Exception in shutting down some '
                              f'of the remaining threads')

        except:
            log.error(self.__LOG_TASKMAN_GRACEFUL_SHUTDOWN,
                      msg=f'Problem in graceful_shutdown')
        finally:
            self.eventLoop.stop()
            log.warning(self.__LOG_TASKMAN_GRACEFUL_SHUTDOWN,
                        msg=f'Done!')

    async def run(
            self) -> None:
        """
        Description :
            Main runner for the Task Manager Class.
        Args:
            None
        Returns :
            None
        """
        try:
            # Launch the MQTT thread listener
            log.warning(self.__LOG_TASKMAN_ASYNC_RUN,
                        msg='Launching MQTT thread.')
            self.threadMQTT = threading.Thread(
                target=self.thread_mqtt_listener, name='thread_mqtt_listener')
            self.threadMQTT.start()
            # Dict that includes exit events (threading.Event)
            self.started_threads[self.threadMQTT] = None

            # Launch event loop tasks in the main thread
            log.warning(self.__LOG_TASKMAN_ASYNC_RUN,
                        msg='Launching asyncio tasks')
            self.event_loop_start_main_tasks()

            # Create a list of tasks that need to be constantly running (used
            # by watchdog)
            self.critical_asyncio_tasks = [
                self.async_process_mqtt_messages_task
            ]

            self.critical_threads = [
                self.threadMQTT,
            ]
            log.info(self.__LOG_TASKMAN_ASYNC_RUN,
                     msg=f'Launching asyncio TASK: "async_watchdog"')
            self.eventLoop.create_task(
                self.async_watchdog(watchdog_timer=5))

        except Exception:
            log.error(self.__LOG_TASKMAN_ASYNC_RUN,
                      f'Error : {traceback.print_exc()}')

    def event_loop_start_main_tasks(
            self):
        """
        Main event asyncio eventloop launched in a separate thread
        """
        try:
            # region Create Async Tasks
            log.info(self.__LOG_TASKMAN_EVENT_LOOP_START_MAIN_TASKS,
                     msg=f'Launching asyncio TASK :"process MQTT message"')
            self.async_process_mqtt_messages_task = \
                self.eventLoop.create_task(
                    self.async_process_mqtt_messages(loopDelay=0.25))
            # endregion

            log.warning(self.__LOG_TASKMAN_EVENT_LOOP_START_MAIN_TASKS,
                        msg=f'Asyncio tasks started')

        except Exception:
            log.error(self.__LOG_TASKMAN_EVENT_LOOP_START_MAIN_TASKS,
                      f'Error : {traceback.print_exc()}')
            raise Exception(f'Error : {traceback.print_exc()}')
        finally:
            log.warning(self.__LOG_TASKMAN_EVENT_LOOP_START_MAIN_TASKS,
                        msg=f'Exiting event_loop_start_main_tasks')

    def thread_mqtt_listener(
            self):
        """
        Description :
            MQTT Thread launching the loop and subscripbing to the right topics
        """
        mqtt_default_qos = 2
        self.mqtt_topics = [(topic, mqtt_default_qos)
                            for topic in self.configuration[
                                'mqtt']['subscribedTopics']]

        def on_connect(client, userdata, flags, rc):
            log.info(self.__LOG_TASKMAN_THREAD_MQTT_LISTENER,
                     msg=f'Connected to MQTT broker. Result code {str(rc)}')
            mqtt_connect_result, self.mqtt_connect_mid = client.subscribe(
                self.mqtt_topics)
            if mqtt_connect_result == mqtt.MQTT_ERR_SUCCESS:
                log.warning(self.__LOG_TASKMAN_THREAD_MQTT_LISTENER,
                            msg=f'Successfully subscribed to '
                                f'topics in input config file')
                log.debug(self.__LOG_TASKMAN_THREAD_MQTT_LISTENER,
                          msg=f'Topics subcribed = {self.mqtt_topics}')
            else:
                log.error(self.__LOG_TASKMAN_THREAD_MQTT_LISTENER,
                          'MQTT Broker subscription problem.')

        def on_message(client, userdata, message):
            """ callback function used for the mqtt client (called when
            a new message is publisehd to one of the queues we subscribe to)
            """
            log.info(self.__LOG_TASKMAN_THREAD_MQTT_LISTENER,
                     msg=f'Received MID {message.mid} : '
                         f'"{str(message.payload)}" '
                         f'on topic {message.topic} with QoS {message.qos}')
            self.mqtt_message_queue.put_nowait(message)

        def on_disconnect(client, userdata, rc=0):
            """callback for handling disconnects
            """
            log.warning(self.__LOG_TASKMAN_THREAD_MQTT_LISTENER,
                        f'Disconnected MQTT result code = {rc}. '
                        f'Should automatically re-connect to broker')

        def on_subscribe(client, userdata, mid, granted_qos):
            if mid == self.mqtt_connect_mid:
                log.debug(self.__LOG_TASKMAN_THREAD_MQTT_LISTENER,
                          msg=f'Subscribed to topics. Granted '
                              f'QOS = {granted_qos}')
            else:
                log.error(self.__LOG_TASKMAN_THREAD_MQTT_LISTENER,
                          msg=f'Strange... MID does not match '
                              f'self.mqtt_connect_mid')

        try:
            self.mqttClient = mqtt.Client(
                client_id=self.configuration["mqtt"]["clientID"],
                clean_session=True,
                transport=self.configuration["mqtt"]["brokerProto"])
            self.mqttClient.enable_logger(
                logger=RoboLogger.getSpecificLogger(
                    self.__LOG_TASKMAN_THREAD_MQTT_LISTENER))
            self.mqttClient.on_subscribe = on_subscribe
            self.mqttClient.on_connect = on_connect
            self.mqttClient.on_disconnect = on_disconnect
            self.mqttClient.on_message = on_message
            self.mqttClient.connect(
                host=self.configuration["mqtt"]["brokerIP"],
                port=self.configuration["mqtt"]["brokerPort"])
            self.mqttClient.loop_forever()
        except Exception:
            log.error(self.__LOG_TASKMAN_THREAD_MQTT_LISTENER,
                      f'Error : {traceback.print_exc()}')
        finally:
            log.warning(self.__LOG_TASKMAN_THREAD_MQTT_LISTENER,
                        msg=f'Exiting MQTT connection thread.')

    async def async_process_mqtt_messages(
            self,
            loopDelay: float = 0.25):
        """
        Description : This function receives the messages from MQTT to the
            task manager.
        Args:
            loopDelay: float, delay to sleep at the end of the loop
        """
        log.warning(self.__LOG_TASKMAN_ASYNC_PROCESS_MQTT_MESSAGES,
                    msg='Launching MQTT processing async task')
        try:
            while True:
                try:
                    if self.mqtt_message_queue.empty() is False:
                        # Remove the first in the list, will pause
                        # until there is something
                        currentMQTTMoveMessage = self.mqtt_message_queue.get()
                        # Decode message received
                        msgdict = json.loads(
                            currentMQTTMoveMessage.payload.decode('utf-8'))

                        # Check if need to shut down
                        if currentMQTTMoveMessage.topic == \
                                'bot/kill_switch':
                            log.warning(
                                self.__LOG_TASKMAN_ASYNC_PROCESS_MQTT_MESSAGES,
                                msg='Kill switch activated')
                            self.kill_switch()
                        elif currentMQTTMoveMessage.topic == \
                                'bot/jetson/configure':
                            log.info(
                                self.__LOG_TASKMAN_ASYNC_PROCESS_MQTT_MESSAGES,
                                msg=f'Modifying configuration item...')
                            for k, v in msgdict.items():
                                if k in dir(self):
                                    log.info(self.__LOG_TASKMAN_ASYNC_PROCESS_MQTT_MESSAGES,        # noqa e501
                                             msg=f'Setting attribute self.{k} '
                                                 f'to value {v}')
                                    # Adding / changing configuration
                                    # parameters for the object
                                    self.__setattr__(k, v)
                                    log.warning(self.__LOG_TASKMAN_ASYNC_PROCESS_MQTT_MESSAGES,         # noqa e501
                                                msg=f'After validation, '
                                                    f'attribute self.{k} '
                                                    f'= "{self.__getattribute__(k)}"')             # noqa e501
                                else:
                                    log.error(self.__LOG_TASKMAN_ASYNC_PROCESS_MQTT_MESSAGES,           # noqa e501
                                              msg=f'Attribute self.{k} not '
                                                  f'found. Will not add it.')
                        elif currentMQTTMoveMessage.topic == \
                                'bot/jetson/logger':
                            # Changing the logging level on the fly...
                            log.setLevel(
                                msgdict['logger'],
                                lvl=msgdict['level'])
                        elif currentMQTTMoveMessage.topic == \
                                'bot/logger/multiple':
                            # Changing the logging level on the fly for
                            # multiple loggers at a time
                            for logger, level in msgdict.items():
                                log.setLevel(logger, level)
                        else:
                            raise NotImplementedError
                    await asyncio.sleep(loopDelay)
                except NotImplementedError:
                    log.warning(self.__LOG_TASKMAN_ASYNC_PROCESS_MQTT_MESSAGES,
                                msg=f'MQTT topic not implemented.')
                except asyncio.futures.CancelledError:
                    log.warning(self.__LOG_TASKMAN_ASYNC_PROCESS_MQTT_MESSAGES,
                                msg=f'Cancelled the MQTT dequeing task.')
                    break
                except Exception:
                    raise
        except Exception:
            log.error(self.__LOG_TASKMAN_ASYNC_PROCESS_MQTT_MESSAGES,
                      msg=f'Error: {traceback.print_exc()}')
            raise

    async def async_watchdog(
            self,
            watchdog_timer: float = 5) -> None:
        """
        Description:
            Watchdog Task : ensures there is a signal to kill the processes
                if main processes/threads/tasks are not healthy.
        Args:
            watchdog_timer : float, seconds between loops
        """
        try:
            while True:
                for task in self.critical_asyncio_tasks:
                    if task.done() or task.cancelled():
                        raise Exception(f'Watchdog - Critical task {task} is '
                                        f'cancelled or done. Need to stop '
                                        f'robot')
                for thread in self.critical_threads:
                    if not thread.is_alive():
                        raise Exception(f'Watchdog - Critical thread '
                                        f'{thread.name} is stopped. Need to '
                                        f'stop object detector.')
                # Capture exceptions from threads as the run function has
                # exited and is unable to catch errors
                try:
                    thread_exception = self.thread_exception_queue.get(
                        block=False)
                except queue.Empty:
                    pass
                else:
                    thread_name, exc_type, exc_obj, exc_trace = \
                        thread_exception
                    # deal with the exception raised in threads IF the threads
                    # aren't terminating with the exception.
                    raise Exception(f'thread_name : {thread_name} ; '
                                    f'exc_type : {exc_type} ; '
                                    f'exc_obj : {exc_obj} ; ')
                log.info(self.__LOG_TASKMAN_ASYNC_WATCHDOG,
                         msg=f'Heartbeat OK - Checking again in '
                             f'{watchdog_timer} seconds')
                await asyncio.sleep(watchdog_timer)
        except asyncio.futures.CancelledError:
            log.warning(self.__LOG_TASKMAN_ASYNC_WATCHDOG,
                        msg=f'Cancelled the watchdog task.')
        except Exception:
            log.critical(self.__LOG_TASKMAN_ASYNC_WATCHDOG,
                         msg=f'Problem with critical task or thread. '
                             f'Need to quit')
            raise

    def kill_switch(
            self):
        """
        Description:
            Kill switch implement to urgently kill processes.
        """
        try:
            log.warning(self.__LOG_TASKMAN_KILL_SWITCH,
                        'Killing process. - to be implemented.')
        except:
            pass
