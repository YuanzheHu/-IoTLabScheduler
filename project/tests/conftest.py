import pytest
from starlette.testclient import TestClient
import logging
import sys
import os

# 添加项目根目录到Python路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

try:
    from main import app
except ImportError:
    # 如果无法导入main，创建一个空的app对象
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
