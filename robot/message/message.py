import uuid
from .message_enums import MessageDirection


class Message(object):
    """
    Description:
        Message class used to exchange information between nodes
    
    """
    def __init__(
            self,
            src_id: uuid,
            dst_id: uuid,
            direction: MessageDirection,
            message_body: dict):
        """
        Description:
            Constructor for the class.
        Args:
            src_id : uuid of the source node of the message
            dst_id : uuid of the destination node of the message
            direction : INBOUND or OUTBOUND
            message_body : k, v pair of relevant information for the message
        """
        self._message_id = uuid.uuid4()
        self.src_id = src_id
        self.dst_id = dst_id
        self.direction = direction
        self.message_body = message_body
