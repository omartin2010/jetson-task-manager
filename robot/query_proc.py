from .message import Message
from .mqtt_engine import MQTTEngine
from .logger import RoboLogger

import asyncio
import traceback
log = RoboLogger()


class QueryProcessor(object):
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
            self) -> None:
        try:
            # Type and value checking if applicable
            # Use the out_msg_q of the singleton MQTTEngine
            self.__mqtt_engine = MQTTEngine()
            self.out_msg_q = self.__mqtt_engine.out_msg_q
            self.in_msg_q = asyncio.Queue()
            log.warning(self.__LOG_INIT,
                        msg=f'Initialized query processor.')
        except:
            log.error(self.__LOG_INIT,
                      msg=f'Error initializing query processor')

    async def query(self,
                    msg: Message = None) -> Message:
        """
        Description:
            Method used to send add message to the queue. Runs async.
        Args:
            msg : used to send the query.
        """
        try:
            # Put message on the queue
            await self.out_msg_q.put(msg)
            self.__mqtt_engine.subscribe_topic(
                callback=self.__cb_get_query_response(),
                topic=msg.topic,
                qos=msg.qos)
            # Wait for incoming response
            await self.in_msg_q.get()
            # Unsubscribe_topic
            self.__mqtt_engine.unsubscribe_topic(msg.topic)
        except asyncio.QueueFull:
            log.error(self.__LOG_SEND_QUERY, msg=f'Outbound queue is full.')
        except Exception:
            raise Exception(f'Error processing query : '
                            f'{traceback.print_exc()}')
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
