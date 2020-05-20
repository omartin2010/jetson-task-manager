from .logger import RoboLogger
from .enums import TaskStatus, StepStatus
from .query_proc import QueryProcessor

from collections import deque
from uuid import uuid4
from abc import ABC, abstractmethod
import time

log = RoboLogger()


class Task(ABC):
    """
    Description:
        Class to create a new task. ABC, has to use a derived task
    """

    __slots__ = ["node_id",
                 "start_time",
                 "end_time",
                 "status",
                 "in_msg_q",
                 "current_step_status",
                 "query_proc"]

    def __init__(self):
        self.node_id = uuid4()
        self.start_time = time.time()
        self.status = TaskStatus.CREATED
        self.in_msg_q = deque()
        self.current_step_status = StepStatus.CREATED
        self.query_proc = QueryProcessor()

    @abstractmethod
    def execute(self):
        raise NotImplementedError

    def get_task_status(self) -> TaskStatus:
        return self.status

    def get_step_status(self) -> StepStatus:
        return self.current_step_status


class SimpleTask(Task):
    def execute(self):
        pass


class ComplexTask(Task):
    def execute(self):
        pass
