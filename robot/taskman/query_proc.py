from robot.common import Message
from robot.common import MQTTEngine
from robot.common import RoboLogger
from . import InboundMessageProcessor

import asyncio
import traceback
from uuid import uuid4
from collections import deque

log = RoboLogger()


class QueryProcessor():
    """
    Description :
        Query message processor, used by every task to query the system
            and get a response.
    """
    __LOG_SEND_QUERY = 'query_processor_send_query'
    __LOG_INIT = 'query_processor_init'

    def __init__(
            self,
            task_response_deque: deque) -> None:
        try:
            # Type and value checking if applicable
            # Use the out_msg_q of the singleton MQTTEngine
            self.__mqtt_engine = MQTTEngine()
            self.out_msg_q = self.__mqtt_engine.out_msg_q
            self.in_msg_q = asyncio.Queue()
            self.task_response_deque = task_response_deque
            self.node_id = uuid4()
            # Retrieve the singleton
            self.__inbound_msg_proc = InboundMessageProcessor()
            self.__inbound_msg_proc.register_query_processor(self)

            log.warning(self.__LOG_INIT,
                        msg=f'Initialized query processor.')
        except Exception:
            log.error(self.__LOG_INIT,
                      msg=f'Error initializing query processor '
                          f'{traceback.print_exc()}')
            raise Exception

    async def query(
            self,
            msg: Message = None) -> Message:
        """
        Description:
            Method used to send add message to the queue. Runs async.
        Args:
            msg : used to send the query.
        """
        try:
            # create and listen to the response on that topic
            self.__mqtt_engine.subscribe_topic(topic=msg.topic, qos=msg.qos)
            # Add msg to queue, it will be processed by mqtt engine
            await self.out_msg_q.put(msg.serialize())
            # Return response (await)
            resp = await self.in_msg_q.get()
            try:
                resp = resp.deserialize()
                if not isinstance(resp, Message):
                    raise TypeError(f'resp has to a Message class')
            except:
                log.error(
                    self.__LOG_SEND_QUERY,
                    msg=f'Error deserializing message response')
            return resp.deserialize()
        except asyncio.QueueFull:
            log.error(self.__LOG_SEND_QUERY, msg=f'Outbound queue is full.')
        except Exception:
            raise Exception(f'Error on query : {traceback.print_exc()}')
        finally:
            self.__mqtt_engine.unsubscribe_topic(msg.topic)
