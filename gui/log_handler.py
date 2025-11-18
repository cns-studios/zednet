"""
Custom logging handler for GUI.
"""
import logging
from queue import Queue

class QueueHandler(logging.Handler):
    """
    Custom logging handler that puts logs into a queue.
    """
    def __init__(self, log_queue: Queue):
        super().__init__()
        self.log_queue = log_queue

    def emit(self, record):
        self.log_queue.put(self.format(record))
