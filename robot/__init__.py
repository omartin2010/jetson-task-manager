from .logger import RoboLogger
from .taskman import TaskManager

__all__ = [
    'TaskManager',
    'RoboLogger'
]

__LOG_TASKMAN_MAIN = 'taskman_main'

log = RoboLogger.getLogger().warning(__LOG_TASKMAN_MAIN, 'taskman imported.')
