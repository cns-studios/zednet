"""
Tests for the AppController.
"""
import pytest
from pathlib import Path
import shutil
from unittest.mock import MagicMock, patch, AsyncMock

from core.app_controller import AppController

@pytest.fixture
def test_env():
    """Set up a test environment."""
    test_dir = Path("./test_env_controller")
    if test_dir.exists():
        shutil.rmtree(test_dir)
    test_dir.mkdir()
    yield test_dir
    shutil.rmtree(test_dir)

def test_app_controller_initialization(test_env):
    """Test that the AppController initializes correctly."""
    controller = AppController(test_env)
    assert controller.data_dir == test_env
    assert controller.storage is not None
    assert controller.publisher is None
    assert controller.downloader is None

def test_app_controller_successful_initialization(test_env):
    """Test the main initialization method of the AppController."""
    controller = AppController(test_env)
    result = controller.initialize()

    assert result is True
    assert controller.publisher is not None
    assert controller.downloader is not None

def test_app_controller_failed_initialization(test_env):
    """Test the main initialization method of the AppController when aiotorrent fails."""
    with patch('core.app_controller.SitePublisher', side_effect=Exception("Failed to start")):
        controller = AppController(test_env)
        result = controller.initialize()

        assert result is False
        assert controller.publisher is None
        assert controller.downloader is None

@pytest.fixture
def initialized_controller(test_env):
    """Fixture for an initialized AppController."""
    controller = AppController(test_env)
    controller.initialize()
    return controller

def test_create_site(initialized_controller):
    """Test the create_site method."""
    mock_publisher = MagicMock()
    initialized_controller.publisher = mock_publisher

    site_name = "test_site"
    content_dir = Path("/fake/dir")
    password = "password123"

    initialized_controller.create_site(site_name, content_dir, password)

    mock_publisher.create_site.assert_called_once_with(site_name, content_dir, password)

@pytest.mark.asyncio
async def test_publish_site(initialized_controller):
    """Test the publish_site method."""
    mock_publisher = MagicMock()
    mock_publisher.publish_site = AsyncMock()
    initialized_controller.publisher = mock_publisher

    site_id = "some_site_id"
    content_dir = Path("/fake/dir")
    private_key_file = Path("/fake/key.pem")
    password = "password123"

    await initialized_controller.publish_site(site_id, content_dir, private_key_file, password)

    mock_publisher.publish_site.assert_called_once_with(site_id, content_dir, private_key_file, password)

@pytest.mark.asyncio
async def test_add_site(initialized_controller):
    """Test the add_site method."""
    mock_downloader = MagicMock()
    mock_downloader.add_site = AsyncMock()
    initialized_controller.downloader = mock_downloader

    site_id = "some_site_id"
    auto_update = False

    await initialized_controller.add_site(site_id, auto_update)

    mock_downloader.add_site.assert_called_once_with(site_id, auto_update)
