import uuid
import pickle


class Message():
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

    def __str__(self):
        print(f'msg_id = {self.msg_id};\n'
              f'src_node_id = {self.src_node_id};\n'
              f'dst_node_id = {self.src_node_id};\n'
              f'body = {self.src_node_id};\n'
              f'topic = {self.src_node_id};\n'
              f'qos = {self.qos};\n')

    def __eq__(self, other) -> bool:
        """
        Description:
            check if all properties are equal...
        Returns True or False
        """
        if type(self) == type(other):
            ret = self.msg_id == other.msg_id and self.src_node_id == \
                other.src_node_id and self.dst_node_id == \
                other.dst_node_id and self.body == \
                other.body and self.topic == \
                other.topic and self.qos == other.qos
        else:
            raise TypeError(f'TypeError - other is {type(other)} '
                            f'and should be Message.')
        return ret

    def serialize(self) -> str:
        """
        Description:
            used to serialize a message before being sent over comm channel
        Returns :
            pickled string, ready to send over the wire.
        """
        payload = pickle.dumps(self)
        return payload

    @staticmethod
    def deserialize(msg):
        """
        Description:
            used to recreate a message ouf of a deserialization operation
        """
        return pickle.loads(msg)
