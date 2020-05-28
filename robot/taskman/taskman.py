# Modules from current package
from ..common import RoboLogger

# Other imports
import queue
import traceback
import threading
import uuid
import asyncio
log = RoboLogger()


class TaskManager():
    """ Main class for the task manager running on the jetson """

    # Defines constants for this class
    __LOG_MAIN = 'taskman_main'
    __LOG_GRACEFUL_SHUTDOWN = 'taskman_graceful_shutdown'
    __LOG_KILL_SWITCH = 'taskman_kill_switch'
    __LOG_ASYNC_RUN = 'taskman_async_run'
    __LOG_ASYNC_WATCHDOG = 'taskman_async_watchdog'
    __LOG_EVENT_LOOP_START_MAIN_TASKS = 'taskman_event_loop_start_main_tasks'
    __LOG_ASYNC_PROCESS_MQTT_MESSAGES = 'taskman_async_process_mqtt_messages'
    __LOG_THREAD_MQTT_LISTENER = 'taskman_thread_mqtt_listener'

    def __init__(
            self,
            configuration: dict,
            loop: asyncio.AbstractEventLoop) -> None:
        self.configuration = configuration
        # self.mqtt_message_queue = queue.Queue()
        self.thread_exception_queue = queue.Queue()
        self.started_threads = {}
        self.eventLoop = loop
        self.node_id = uuid.uuid4()

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
                log.critical(self.__LOG_GRACEFUL_SHUTDOWN,
                             msg=f'Initiating graceful shutdown now '
                                 f'from received signal {s.name}.')
            else:
                log.critical(self.__LOG_GRACEFUL_SHUTDOWN,
                             msg=f'Initiating graceful shutdown now '
                                 f'from non signal.')
            # region asyncio event loop tasks
            try:
                tasks = [t for t in asyncio.Task.all_tasks(loop=self.eventLoop)
                         if t is not asyncio.Task.current_task()]
                log.info(self.__LOG_GRACEFUL_SHUTDOWN,
                         msg=f'Cancelling task {len(tasks)} tasks...')
                [task.cancel() for task in tasks]
                log.info(self.__LOG_GRACEFUL_SHUTDOWN,
                         msg=f'Gaterhing out put of cancellation '
                             f'of {len(tasks)} tasks...')
                out_list = await asyncio.gather(
                    *tasks,
                    loop=self.eventLoop,
                    return_exceptions=True)
                for idx, out in enumerate(out_list):
                    if isinstance(out, Exception):
                        log.error(self.__LOG_GRACEFUL_SHUTDOWN,
                                  msg=f'Exception in stopping task {idx}')
                log.warning(self.__LOG_GRACEFUL_SHUTDOWN,
                            msg=f'Done cancelling tasks.')
            except:
                pass
            # endregion asyncio event loop tasks

            # # Stop MQTT client:
            # try:
            #     self.mqttClient.loop_stop()
            #     self.mqttClient.disconnect()
            #     if self.mqttClient.is_connected():
            #         log.error(self.__LOG_TASKMAN_GRACEFUL_SHUTDOWN,
            #                   msg=f'Unable to stop MQTT client.')
            #     else:
            #         log.info(self.__LOG_TASKMAN_GRACEFUL_SHUTDOWN,
            #                  msg=f'Stopped MQTT client.')
            # except:
            #     log.error(self.__LOG_TASKMAN_GRACEFUL_SHUTDOWN,
            #               msg=f'Exception in shutting down MQTT')

            try:
                # Stop remaining threads
                for thread, event in self.started_threads.items():
                    if thread.is_alive():
                        event.set()
                        await asyncio.sleep(0.5)
                        if thread.is_alive():
                            log.error(self.__LOG_GRACEFUL_SHUTDOWN,
                                      msg=f'Problem shutting down '
                                          f'some threads!')
            except:
                log.error(self.__LOG_GRACEFUL_SHUTDOWN,
                          msg=f'Exception in shutting down some '
                              f'of the remaining threads')

        except:
            log.error(self.__LOG_GRACEFUL_SHUTDOWN,
                      msg=f'Problem in graceful_shutdown')
        finally:
            self.eventLoop.stop()
            log.warning(self.__LOG_GRACEFUL_SHUTDOWN,
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
            log.warning(self.__LOG_ASYNC_RUN,
                        msg='Launching MQTT thread.')
            self.threadMQTT = threading.Thread(
                target=self.thread_mqtt_listener, name='thread_mqtt_listener')
            self.threadMQTT.start()
            # Dict that includes exit events (threading.Event)
            self.started_threads[self.threadMQTT] = None

            # Launch event loop tasks in the main thread
            log.warning(self.__LOG_ASYNC_RUN,
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
            log.info(self.__LOG_ASYNC_RUN,
                     msg=f'Launching asyncio TASK: "async_watchdog"')
            self.eventLoop.create_task(
                self.async_watchdog(watchdog_timer=5))

        except Exception:
            log.error(self.__LOG_ASYNC_RUN,
                      f'Error : {traceback.print_exc()}')

    def event_loop_start_main_tasks(
            self):
        """
        Main event asyncio eventloop launched in a separate thread
        """
        try:
            # region Create Async Tasks
            log.info(self.__LOG_EVENT_LOOP_START_MAIN_TASKS,
                     msg=f'Launching asyncio TASK :"process MQTT message"')
            self.async_process_mqtt_messages_task = \
                self.eventLoop.create_task(
                    self.async_process_mqtt_messages(loopDelay=0.25))
            # endregion

            log.warning(self.__LOG_EVENT_LOOP_START_MAIN_TASKS,
                        msg=f'Asyncio tasks started')

        except Exception:
            log.error(self.__LOG_EVENT_LOOP_START_MAIN_TASKS,
                      f'Error : {traceback.print_exc()}')
            raise Exception(f'Error : {traceback.print_exc()}')
        finally:
            log.warning(self.__LOG_EVENT_LOOP_START_MAIN_TASKS,
                        msg=f'Exiting event_loop_start_main_tasks')

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
                log.info(self.__LOG_ASYNC_WATCHDOG,
                         msg=f'Heartbeat OK - Checking again in '
                             f'{watchdog_timer} seconds')
                await asyncio.sleep(watchdog_timer)
        except asyncio.futures.CancelledError:
            log.warning(self.__LOG_ASYNC_WATCHDOG,
                        msg=f'Cancelled the watchdog task.')
        except Exception:
            log.critical(self.__LOG_ASYNC_WATCHDOG,
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
            log.warning(self.__LOG_KILL_SWITCH,
                        'Killing process. - to be implemented.')
        except:
            pass
