from robot.common import RoboLogger
from robot.taskman.enums import TaskStatus, StepStatus
from . import QueryProcessor

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

    def __init__(self):
        self.node_id = uuid4()
        self.start_time = time.time()
        self.status = TaskStatus.CREATED
        self.in_msg_q = deque()
        self.current_step_status = StepStatus.CREATED
        self.query_proc = QueryProcessor(self.in_msg_q)

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
