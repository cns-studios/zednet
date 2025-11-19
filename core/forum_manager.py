# core/forum_manager.py
import json
from pathlib import Path
import logging
from datetime import datetime
from typing import Dict, List, Optional
import uuid
import torf
import aiotorrent

logger = logging.getLogger(__name__)

class ForumManager:
    """
    Manages the forum data, including loading, saving, and updating posts.
    """

    def __init__(self, storage_dir: Path, downloader: 'SiteDownloader'):
        self.storage_dir = storage_dir
        self.forum_file = self.storage_dir / "forum_data.json"
        self.forum_torrent_file = self.storage_dir / "forum.torrent"
        self.forum_data = self._load_data()
        self.downloader = downloader

    def _load_data(self) -> Dict:
        """Loads forum data from the JSON file."""
        if not self.forum_file.exists():
            return {"posts": []}
        try:
            with open(self.forum_file, 'r', encoding='utf-8') as f:
                return json.load(f)
        except (IOError, json.JSONDecodeError):
            logger.exception("Could not read or parse forum data file.")
            return {"posts": []}

    def _save_data(self):
        """Saves the current forum data to the JSON file."""
        try:
            with open(self.forum_file, 'w', encoding='utf-8') as f:
                json.dump(self.forum_data, f, indent=2)
        except IOError:
            logger.exception("Could not save forum data file.")

    def get_all_posts(self) -> Dict:
        """Returns all forum data."""
        return self.forum_data

    def add_post(self, author: str, content: str) -> Optional[Dict]:
        """Adds a new post to the forum."""
        new_post = {
            "post_id": str(uuid.uuid4()),
            "author": author,
            "content": content,
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "replies": [],
            "votes": {"up": [], "down": []}
        }
        self.forum_data["posts"].append(new_post)
        self._save_data()
        return new_post

    def add_reply(self, post_id: str, author: str, content: str) -> Optional[Dict]:
        """Adds a reply to a specific post."""
        post = next((p for p in self.forum_data["posts"] if p["post_id"] == post_id), None)
        if not post:
            return None

        new_reply = {
            "reply_id": str(uuid.uuid4()),
            "author": author,
            "content": content,
            "timestamp": datetime.utcnow().isoformat() + "Z",
        }
        post["replies"].append(new_reply)
        self._save_data()
        return new_reply

    def vote(self, post_id: str, user_id: str, direction: str) -> bool:
        """Casts a vote on a post."""
        post = next((p for p in self.forum_data["posts"] if p["post_id"] == post_id), None)
        if not post or direction not in ["up", "down"]:
            return False

        # Simple model: user can only vote up or down, not both
        if direction == "up":
            if user_id not in post["votes"]["up"]:
                post["votes"]["up"].append(user_id)
                if user_id in post["votes"]["down"]:
                    post["votes"]["down"].remove(user_id)
        elif direction == "down":
            if user_id not in post["votes"]["down"]:
                post["votes"]["down"].append(user_id)
                if user_id in post["votes"]["up"]:
                    post["votes"]["up"].remove(user_id)

        self._save_data()
        return True

    def merge_data(self, other_data: Dict) -> bool:
        """Merges incoming forum data with local data."""
        if "posts" not in other_data:
            return False

        local_post_ids = {p["post_id"] for p in self.forum_data["posts"]}
        changed = False

        for post in other_data["posts"]:
            if post["post_id"] not in local_post_ids:
                self.forum_data["posts"].append(post)
                changed = True
            else:
                # More complex merging logic for replies/votes would go here
                pass

        if changed:
            self._save_data()
            self.update_and_seed_forum_torrent()

        return changed

    def get_forum_site_id(self) -> str:
        """
        Returns the site_id for the forum.
        For now, this is a placeholder. A real implementation might use a known public key.
        """
        return "forum_site_id_placeholder"

    def update_and_seed_forum_torrent(self):
        """Creates and seeds a torrent for the forum data."""
        try:
            t = torf.Torrent(path=str(self.forum_file), trackers=[])
            t.generate()
            t.write(str(self.forum_torrent_file))
            logger.info("Created forum torrent at %s", self.forum_torrent_file)
            # In a full implementation, we would start seeding this torrent.
        except Exception as e:
            logger.error("Failed to create forum torrent: %s", e)

    async def sync_forum(self):
        """Downloads the latest forum data from the network and merges it."""
        site_id = self.get_forum_site_id()
        if await self.downloader.add_site(site_id, auto_update=True):
            # The downloader will handle fetching the latest version.
            # We can then load the updated file from the downloads directory.
            downloaded_file = self.downloader.storage.get_content_path(site_id) / "forum_data.json"
            if downloaded_file.exists():
                try:
                    with open(downloaded_file, 'r', encoding='utf-8') as f:
                        other_data = json.load(f)
                    self.merge_data(other_data)
                except (IOError, json.JSONDecodeError):
                    logger.error("Failed to read or parse downloaded forum data.")
