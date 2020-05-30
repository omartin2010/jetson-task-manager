from robot import RoboLogger
from robot import Message
from robot import MQTTEngine
from robot.common.singleton import Singleton

import asyncio
from collections import deque
import traceback
from uuid import uuid4

log = RoboLogger()


class InboundMessageProcessor(metaclass=Singleton):
    """
    Description:
        Class, singleton, to manage inbound messages
    """

    __slots__ = ["event_loop",
                 "in_msg_q",
                 "recipient_map",
                 "__mqtt_engine",
                 "__running"]

    def __init__(
            self,
            event_loop: asyncio.BaseEventLoop,
            taskman_node_id: uuid4,
            mqtt_configuration: dict) -> None:
        """
        Description :
            Constructor.
        Args:
            mqtt_configuration : dict, configuration dict that tells where to
                connect, which topics to listen to, etc.
            event_loop : event loop for the runner
            taskman_node_id : instance node id of the task manager
        """
        try:
            # Type and value checking
            if not isinstance(mqtt_configuration, dict):
                raise TypeError('mqtt_configuration has to be a dictionnary')
            if not isinstance(event_loop, asyncio.BaseEventLoop):
                raise TypeError(f'Constructor requires event_loop to be of '
                                f'asyncio.BaseEventLoop() class')
            if not isinstance(taskman_node_id, uuid4):
                raise TypeError(f'Constructor requires taskman to be of type '
                                f'uuid4')
            self.event_loop = event_loop
            self.__mqtt_engine = MQTTEngine(
                mqtt_configuration=mqtt_configuration,
                event_loop=self.event_loop)
            self.in_msg_q = self.__mqtt_engine.in_msg_q
            self.recipient_map = {taskman_node_id: deque()}
            self.__running = False
        except Exception:
            raise (f'Problem in init : traceback = {traceback.print_exc()}')

    async def run(self) -> None:
        """
        Description:
            starts the runner
        """
        try:
            # Launch the MQTT engine
            self.__mqtt_engine.run()
            self.__running = True
            while self.__running:
                # Get q'd message from engine
                msg = Message(await self.__mqtt_engine.in_msg_q.get())
                # Get the proper Q for the target
                q = deque(self.recipient_map[msg.dst_node_id])
                q.extend(msg)
        except:
            pass

    def register_item(
            self,
            item_node_id: uuid4) -> None:
        """
        Description:
            Used to register a new itemto the recipient map, so that inbound
                messages are sent to the right queue for processing

        """
        if not isinstance(item_node_id, uuid4):
            raise TypeError('task has to be of type Task')
        self.recipient_map[item_node_id.node_id] = item_node_id.in_msg_q

    def graceful_shutdown(self) -> None:
        """
        Description:
            Used to gracefully shut down the message processor
        """
        self.__running = False
