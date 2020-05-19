import uuid


class Message(object):
    """
    Description:
        Message class used to exchange information between nodes
    """
    def __init__(
            self,
            src_node_id: uuid.UUID,
            dst_node_id: uuid.UUID,
            body: dict,
            topic: str,
            qos: int = 1):
        """
        Description:
            Constructor for the class.
        Args:
            src_node_id : uuid of the source node of the message
            dst_node_id : uuid of the destination node of the message
            direction : INBOUND or OUTBOUND
            body : k, v pair of relevant information for the message
            topic : string : topic of the message ? maybe dst_id??
            qos : int, 0, 1 or 2, used for MQTT
        """
        # Type and value checking
        if not isinstance(src_node_id, uuid.UUID):
            raise TypeError(f'src_id has to be a UUID')
        if not isinstance(dst_node_id, uuid.UUID):
            raise TypeError(f'dst_id has to be a UUID')
        if not isinstance(body, dict):
            raise TypeError(f'body has to be a dict')
        if not isinstance(topic, str):
            raise TypeError(f'topic has to be a str')
        if qos not in [0, 1, 2]:
            raise ValueError(f'QOS has to be 0, 1 or 2')
        self.msg_id = uuid.uuid4()
        self.src_node_id = src_node_id
        self.dst_node_id = dst_node_id
        self.body = body
        self.topic = topic
        self.qos = qos
