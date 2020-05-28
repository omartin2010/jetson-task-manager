from ..common import Message
from ..common import MQTTEngine
from ..common import RoboLogger
from .inbound_message_processor import InboundMessageProcessor

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
    __LOG__CB_GET_QUERY_RESPONSE = 'query_processor_cb_get_query_response'

    __slots__ = ['__mqtt_engine',
                 'out_msg_q',
                 'in_msg_q']

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
            self.__id = uuid4()
            # Register the query processor
            self.__inbound_msg_proc = InboundMessageProcessor()
            self.__inbound_msg_proc.register_query_processor(self)

            log.warning(self.__LOG_INIT, msg=f'Initialized query processor.')
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
            await self.out_msg_q.put(msg)
            # Return response (await)
            return await self.in_msg_q.get()
        except asyncio.QueueFull:
            log.error(self.__LOG_SEND_QUERY, msg=f'Outbound queue is full.')
        except Exception:
            raise Exception(f'Error on query : {traceback.print_exc()}')
        finally:
            self.__mqtt_engine.unsubscribe_topic(msg.topic)

    def __cb_get_query_response(
            self,
            client,
            userdata,
            message):
        """
        Description:
            callback used to get query response back
        Args:
            client :
            userdata :
            message :
        """
        try:
            # Add response message to queue!
            self.in_msg_q.put(message)

        except asyncio.QueueFull:
            log.error(self.__LOG__CB_GET_QUERY_RESPONSE,
                      msg=f'Outbound queue is full.')
        except Exception:
            log.error(self.__LOG__CB_GET_QUERY_RESPONSE,
                      msg=f'Error in callback to queue ')
