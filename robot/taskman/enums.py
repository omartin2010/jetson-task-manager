from enum import IntEnum


class TaskStatus(IntEnum):
    CREATED = 1
    STARTED = 2
    CRASHED = 3
    FINISHED = 4
    SUCCESS = 5


class StepStatus(IntEnum):
    CREATED = 1
    STARTED = 2
    CRASHED = 3
    FINISHED = 4
    SUCCESS = 5
