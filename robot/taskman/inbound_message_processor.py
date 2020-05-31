from robot import RoboLogger
from robot import Message
from robot import MQTTEngine
from robot.common.singleton import Singleton

import asyncio
from collections import deque
import traceback
from uuid import uuid4, UUID

log = RoboLogger()


class InboundMessageProcessor(metaclass=Singleton):
    """
    Description:
        Class, singleton, to manage inbound messages
    """

    def __init__(
            self,
            event_loop: asyncio.BaseEventLoop,
            mqtt_configuration: dict) -> None:
        """
        Description :
            Constructor.
        Args:
            mqtt_configuration : dict, configuration dict that tells where to
                connect, which topics to listen to, etc.
            event_loop : event loop for the runner
        """
        try:
            # Type and value checking
            if not isinstance(mqtt_configuration, dict):
                raise TypeError('mqtt_configuration has to be a dictionnary')
            if not isinstance(event_loop, asyncio.BaseEventLoop):
                raise TypeError(f'Constructor requires event_loop to be of '
                                f'asyncio.BaseEventLoop() class')
            self.event_loop = event_loop
            self.__mqtt_engine = MQTTEngine(
                mqtt_configuration=mqtt_configuration,
                event_loop=self.event_loop)
            self.in_msg_q = self.__mqtt_engine.in_msg_q
            self.recipient_map = {}  # {taskman_node_id: deque()}
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
                msg = await self.__mqtt_engine.in_msg_q.get()
                # Get the proper Q for the target
                q = deque(self.recipient_map[msg.dst_node_id])
                q.extend(msg)
        except:
            pass

    def register(
            self,
            node_id: UUID,
            in_msg_q: asyncio.Queue) -> None:
        """
        Description:
            Used to register a new itemto the recipient map, so that inbound
                messages are sent to the right queue for processing
        Args:
            node_id : id of the node that registers (uuid)
            in_msg_q : queue that needs to be registered
        """
        if not isinstance(node_id, UUID):
            raise TypeError('node_id has to be of type UUID')
        if not isinstance(in_msg_q, asyncio.Queue):
            raise TypeError('in_msg_q has to be of type asyncio.Queue')
        self.recipient_map[node_id] = in_msg_q

    @staticmethod
    def get_instance():
        return Singleton._instances[__class__]

    def graceful_shutdown(self) -> None:
        """
        Description:
            Used to gracefully shut down the message processor
        """
        self.__running = False
