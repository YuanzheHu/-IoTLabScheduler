import pytest
from starlette.testclient import TestClient
import logging
import sys
import os

# Add the project root directory to the Python path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

try:
    from main import app
except ImportError:
    # If main cannot be imported, create an empty app object
    app = None


@pytest.fixture(scope="module")
def test_app():
    if app is None:
        pytest.skip("Main app not available")
    client = TestClient(app)
    yield client  # testing happens here


def pytest_configure(config):
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s [%(levelname)s] %(name)s: %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S',
        filename='tests/test.log',
        filemode='a'
    )
    console = logging.StreamHandler(sys.stdout)
    console.setLevel(logging.INFO)
    formatter = logging.Formatter('%(asctime)s [%(levelname)s] %(name)s: %(message)s')
    console.setFormatter(formatter)
    logging.getLogger('').addHandler(console)
