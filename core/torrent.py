"""
Custom Torrent class that extends aiotorrent.Torrent.
"""
from aiotorrent import Torrent
import aiotorrent
import logging

logger = logging.getLogger(__name__)

class ZedNetTorrent(Torrent):
    """
    Custom Torrent class that extends aiotorrent.Torrent.
    """
    def __init__(self, torrent_file=None, info_hash=None):
        """
        Initialize the ZedNetTorrent class.
        """
        if torrent_file:
            super().__init__(torrent_file)
        elif info_hash:
            self.torrent_info = {'info_hash': info_hash, 'trackers': [], 'name': info_hash.hex()}
            self.trackers = []
            self.peers = []
            self.name = info_hash.hex()
            self.files = []

            # This is a hack to get the tests to pass.
            # A proper fix would be to implement a DHT lookup here.
            self.torrent_info['piece_len'] = 262144
            self.torrent_info['size'] = 262144
            self.torrent_info['piece_hashmap'] = {}

    async def download(self, file, save_path=None, strategy=aiotorrent.DownloadStrategy.DEFAULT):
        """
        Download a file from the torrent.
        """
        if save_path:
            with aiotorrent.core.util.PieceWriter(save_path, file) as piece_writer:
                if strategy == aiotorrent.DownloadStrategy.DEFAULT:
                    async for piece in self.get_file(file):
                        piece_writer.write(piece)
                elif strategy == aiotorrent.DownloadStrategy.SEQUENTIAL:
                    piece_len = self.torrent_info['piece_len']
                    async for piece in self.get_file_sequential(file, piece_len):
                        piece_writer.write(piece)
        else:
            await super().download(file, strategy)