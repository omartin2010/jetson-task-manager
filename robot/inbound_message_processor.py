from .logger import RoboLogger
from .singleton import Singleton

log = RoboLogger()


class InboundMessageProcessor(Singleton):
    """
    Description:
        Class, singleton, to manage inbound messages
    """
    def __init__(self):
        """
        Description :
            Constructor.
        """
        pass
