"""
Tests for the site downloader.
"""
import asyncio
from pathlib import Path
import shutil
import logging
import pytest
from unittest.mock import patch, AsyncMock, MagicMock
from core.publisher import SitePublisher
from core.downloader import SiteDownloader
from core.storage import SiteStorage

@pytest.fixture
def test_env():
    """Set up a test environment."""
    test_dir = Path("./test_env")
    if test_dir.exists():
        shutil.rmtree(test_dir)
    test_dir.mkdir(exist_ok=True)
    yield test_dir
    shutil.rmtree(test_dir)

@pytest.mark.asyncio
async def test_download_site(test_env):
    """
    Test downloading a site from a peer.
    """
    logging.basicConfig(level=logging.INFO, format='%(asctime)s | %(levelname)-8s | %(name)-15s | %(message)s')

    storage = SiteStorage(test_env / "sites")
    downloader = SiteDownloader(storage)

    # 1. Create dummy metadata for a site
    site_id = "a0cb9dbcb48b8c31ec6d0dde1e9fb50986092ff32a687eee2a83517b6a2e63e0"
    storage.save_site_metadata(
        site_id,
        {
            "public_key": "dummy_public_key",
            "site_id": site_id,
            "site_name": "My Test Site",
        },
    )

    # 2. Mock the DHT lookup and the Torrent object
    with patch('core.downloader.SiteDownloader._lookup_site_in_dht', new_callable=AsyncMock) as mock_lookup:
        mock_lookup.return_value = b'01234567890123456789'

        mock_torrent_instance = MagicMock()
        mock_torrent_instance.init = AsyncMock()
        mock_torrent_instance.download = AsyncMock()
        mock_file = MagicMock()
        mock_torrent_instance.files = [mock_file]

        with patch('core.downloader.Torrent', return_value=mock_torrent_instance) as mock_torrent_class:

            # 3. Run the downloader
            success = await downloader.add_site(site_id)

            # 4. Assert the results
            assert success, "Failed to add site to downloader"
            assert site_id in downloader.active_downloads

            dummy_torrent_path = storage.get_site_content_dir(site_id) / "metadata.torrent"
            assert dummy_torrent_path.exists(), "Dummy torrent file was not created"

            mock_torrent_class.assert_called_once_with(str(dummy_torrent_path))
            mock_torrent_instance.init.assert_awaited_once()
