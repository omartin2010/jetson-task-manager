# flake8: ignore=E501
from .singleton import Singleton

import logging


class RoboLogger(metaclass=Singleton):
    """
    Description :
        Implementation of a logger object for debugging independently
            all parts of the robot
    Singleton pattern :
    https://stackoverflow.com/questions/6760685/creating-a-singleton-in-python
    """

    __instance = None
    __loggers = []

    def __init__(self, defaultLevel=logging.WARNING):
        '''
        Initializes the main logger
        loggerName : str : name of the logger
        defaultLevel : logging.INFO, ...
        '''
        self.defaultLevel = defaultLevel
        self.__addNewLogger('root', self.defaultLevel)

    @staticmethod
    def get_instance():
        return Singleton._instances[__class__]

    @staticmethod
    def getSpecificLogger(loggerName: str) -> logging.Logger:
        if loggerName in RoboLogger.__loggers:
            return logging.getLogger()

    @staticmethod
    def __addNewLogger(loggerName: str, defaultLevel: int) -> None:
        logger = logging.getLogger(loggerName)
        logger.setLevel(defaultLevel)
        ch = logging.StreamHandler()
        ch.setLevel(defaultLevel)
        ch.setFormatter(logging.Formatter(
            fmt='%(asctime)s.%(msecs)03d:PID%(process)d:%(levelname)s:%(threadName)s:%(name)s:%(message)s',    # noqa E501
            datefmt='%Y-%m-%d %H:%M:%S'))
        logger.addHandler(ch)
        RoboLogger.__loggers.append(loggerName)

    # @staticmethod
    def setLevel(self, loggerName: str, lvl: int) -> None:
        '''
        loggername:str:name of the current logger
        lvl:int (maybe):logging.DEBUG, logging.INFO, logging.WARNING, etc.
        '''
        if lvl in [logging.DEBUG, logging.INFO, logging.WARNING,
                   logging.ERROR, logging.CRITICAL]:
            if loggerName in RoboLogger.__loggers:
                # change the level for the main logger
                if lvl is not logging.getLogger(loggerName).level:
                    logging.getLogger('root').critical(
                        f'Changing logger \'{loggerName}\' level '
                        f'{logging.getLogger(loggerName).level} ==> {lvl}')
                    logging.getLogger(loggerName).setLevel(lvl)
                # change level for the handlers:
                for handler in logging.getLogger(loggerName).handlers:
                    handler.setLevel(lvl)
            # logger doesn't yet exist
            else:
                logging.getLogger('root').critical(
                    f'Setting logging level on non existing logger - '
                    f'Creating logger \'{loggerName}\' with level {lvl}')
                self.__addNewLogger(loggerName, lvl)

    def critical(self, loggerName: str, msg: str, *args, **kwargs) -> None:
        if loggerName not in RoboLogger.__loggers:
            self.__addNewLogger(loggerName, self.defaultLevel)
        logging.getLogger(loggerName).critical(msg, *args, **kwargs)

    def error(self, loggerName: str, msg: str, *args, **kwargs) -> None:
        if loggerName not in RoboLogger.__loggers:
            self.__addNewLogger(loggerName, self.defaultLevel)
        logging.getLogger(loggerName).error(msg, *args, **kwargs)

    def warning(self, loggerName: str, msg: str, *args, **kwargs) -> None:
        if loggerName not in RoboLogger.__loggers:
            self.__addNewLogger(loggerName, self.defaultLevel)
        logging.getLogger(loggerName).warning(msg, *args, **kwargs)

    def info(self, loggerName: str, msg: str, *args, **kwargs) -> None:
        if loggerName not in RoboLogger.__loggers:
            self.__addNewLogger(loggerName, self.defaultLevel)
        logging.getLogger(loggerName).info(msg, *args, **kwargs)

    def debug(self, loggerName: str, msg: str, *args, **kwargs) -> None:
        if loggerName not in RoboLogger.__loggers:
            self.__addNewLogger(loggerName, self.defaultLevel)
        logging.getLogger(loggerName).debug(msg, *args, **kwargs)
