
import pytest
from nornir import InitNornir
@pytest.fixture(scope="session", autouse=True)
def pytestnr():
    pytestnr = InitNornir(config_file="prodconfig.yaml")
    yield pytestnr
    pytestnr.close_connections()
