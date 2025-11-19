"""
Integration tests for the site directory registration and viewing flow.
"""
import pytest
from flask import Flask
import json
from pathlib import Path
import shutil
import asyncio

from core.app_controller import AppController

def test_directory_flow():
    """Test the full site registration and viewing flow."""
    data_dir = Path('./test_data')
    if data_dir.exists():
        shutil.rmtree(data_dir)
    data_dir.mkdir(exist_ok=True)

    # Create empty submissions and sites files
    with open(data_dir / 'submissions.json', 'w') as f:
        json.dump([], f)
    with open(data_dir / 'sites.json', 'w') as f:
        json.dump([], f)

    from server.local_server import create_app, initialize_server
    from core.app_controller import AppController

    app = create_app()
    controller = AppController(data_dir)
    controller.initialize()

    initialize_server(None, data_dir / 'sites', controller)

    app.config['TESTING'] = True

    with app.test_client() as client:
        # 1. Register a new site
        response = client.post('/register', data={
            'site_name': 'Test Site',
            'info_hash': 'a' * 40  # 40-char hex string
        })
        assert response.status_code == 200
        assert b"Site submitted for review" in response.data

        # 2. Approve the site
        response = client.post('/admin/approve', data={
            'info_hash': 'a' * 40
        })
        assert response.status_code == 200
        assert b"Site approved" in response.data

        # 3. View the directory
        # We need to mock the directory download, since we're not running a full P2P network
        # For this test, we'll just check that the sites.json file is updated
        sites_json_path = Path('./test_data/sites.json')
        assert sites_json_path.exists()

        with open(sites_json_path, 'r') as f:
            sites = json.load(f)

        assert len(sites) == 1
        assert sites[0]['site_name'] == 'Test Site'
        assert sites[0]['info_hash'] == 'a' * 40

    # Teardown
    shutil.rmtree(data_dir)
