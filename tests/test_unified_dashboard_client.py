import shutil
import subprocess

import pytest


def test_dashboard_client_routes_both_markets():
    node = shutil.which("node")
    if not node:
        pytest.skip("Node required for browser adapter test")
    subprocess.run([node, "tests/unified-dashboard.test.mjs"], check=True, capture_output=True)
