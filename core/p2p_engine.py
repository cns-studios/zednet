"""
P2P engine using aiotorrent.
Initializes and manages the asyncio event loop.
"""
import asyncio
import logging

logger = logging.getLogger(__name__)

class P2PEngine:
    """
    Manages the asyncio event loop.
    """
    
    def __init__(self):
        self.loop = asyncio.get_event_loop()

    def get_loop(self):
        return self.loop
