"""
Tests for the site downloader.
"""
import asyncio
from pathlib import Path
import shutil
import logging
import pytest
from core.p2p_engine import P2PEngine
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

    engine = P2PEngine()
    storage = SiteStorage(test_env / "sites")
    publisher = SitePublisher(storage)
    downloader = SiteDownloader(storage)

    content_dir = test_env / "site_content"
    content_dir.mkdir()
    (content_dir / "index.html").write_text("<html><body>Hello, Downloader!</body></html>")

    site_info = publisher.create_site("My Test Site", content_dir)
    await publisher.publish_site(
        site_info["site_id"], content_dir, Path(site_info["private_key_file"])
    )

    storage.save_site_metadata(
        site_info["site_id"],
        {"public_key": site_info["public_key"], "site_id": site_info["site_id"]},
    )

    success = await downloader.add_site(site_info["site_id"])
    assert success, "Failed to add site to downloader"

    # Wait for the download to complete
    for _ in range(120):
        status = downloader.get_site_status(site_info["site_id"])
        if status and status["progress"] == 1.0:
            break
        await asyncio.sleep(1)

    # Verify the downloaded content
    downloaded_file = downloader.storage.get_site_content_path(site_info["site_id"]) / "index.html"
    assert downloaded_file.exists(), "Downloaded file does not exist"
    assert downloaded_file.read_text() == "<html><body>Hello, Downloader!</body></html>"
