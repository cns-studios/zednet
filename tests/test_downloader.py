"""
Tests for the site downloader.
"""
import asyncio
from pathlib import Path
import shutil
import logging
import pytest
from unittest.mock import patch, AsyncMock
from core.publisher import SitePublisher
from core.downloader import SiteDownloader
from core.storage import SiteStorage

@pytest.fixture
def test_env():
    """Set up a test environment."""
    test_dir = Path("./test_env")
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
    publisher = SitePublisher(storage)
    downloader = SiteDownloader(storage)

    content_dir = test_env / "site_content"
    content_dir.mkdir(exist_ok=True)
    (content_dir / "index.html").write_text("<html><body>Hello, Downloader!</body></html>")

    site_info = publisher.create_site("My Test Site", content_dir)
    await publisher.publish_site(
        site_info["site_id"], content_dir, Path(site_info["private_key_file"])
    )

    storage.save_site_metadata(
        site_info["site_id"],
        {"public_key": site_info["public_key"], "site_id": site_info["site_id"]},
    )

    # This test is a placeholder, as it requires a live DHT to resolve the site.
    # In a real-world scenario, you would need a more sophisticated testing setup
    # with a local DHT or a mocked DHT response.
    with patch('core.downloader.SiteDownloader._lookup_site_in_dht', new_callable=AsyncMock) as mock_lookup:
        # Simulate a successful DHT lookup by returning a dummy info_hash
        mock_lookup.return_value = b'dummy_info_hash_12345678901234567890'

        success = await downloader.add_site(site_info["site_id"])
        assert success, "Failed to add site to downloader"

        # Further testing would require a running torrent client to download the content.
        # For now, we'll just verify that the site was added to the downloader.
        assert site_info["site_id"] in downloader.active_downloads
