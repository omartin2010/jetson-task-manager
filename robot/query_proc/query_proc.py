from ..message import Message
from ..mqtt import MQTTEngine
from ..logger import RoboLogger

import asyncio
log = RoboLogger.getLogger()


class QueryProcessor(object):
    """
    Description :
        Query message processor, used by every task to query the system
            and get a response.
    """
    __LOG_SEND_QUERY = 'query_processor_send_query'

    def __init__(
            self) -> None:
        try:
            # Type and value checking if applicable
            # Use the out_msg_q of the singleton MQTTEngine
            self.__mqtt_engine = MQTTEngine()
            self.outbound_msg_q = self.__mqtt_engine.out_msg_q
            self.in_msg_q = asyncio.Queue()
        except:
            pass

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
            await self.outbound_msg_q.put(msg)
            self.__mqtt_engine.subscribe_topic(
                callback=self.__cb_get_query_response(),
                topic=msg.topic,
                qos=msg.qos)
            # Wait for incoming response
            await self.in_msg_q.get()
        except asyncio.QueueFull:
            log.error(self.__LOG_SEND_QUERY, msg=f'Outbound queue is full.')

    def __cb_get_query_response(
            self,
            client,
            userdata,
            message):
        """
        Description:
            callback used by query
        """
        pass
