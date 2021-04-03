
import pytest
from nornir import InitNornir
@pytest.fixture(scope="session", autouse=True)
def pytestnr():
    pytestnr = InitNornir(config_file="testconfig.yaml")
    yield pytestnr
    pytestnr.close_connections()
