"""
Author: John McGovern (IPvZero)
"""
import os
import requests
import pytest
from nornir import InitNornir
from nornir.core.filter import F
from nornir_utils.plugins.tasks.data import load_yaml


nr = InitNornir(config_file="testconfig.yaml")
nr.inventory.defaults.username = os.getenv("USERNAME")
nr.inventory.defaults.password = os.getenv("PASSWORD")

headers = {
    "Accept": "application/yang-data+json",
}

def load_vars(task):
    """
    Load Desired State
    """
    result = task.run(
        task=load_yaml, file=f"/home/ipvzero/Project/host_vars/{task.host}.yaml"
    )
    task.host["loaded_vars"] = result.result


def get_ntp_servers(task):
    """
    Pull NTP Information via RESTCONF
    """
    url = f"https://{task.host.hostname}:443/restconf/data/native/ntp"
    server_list = []
    response = requests.get(
        url=url,
        headers=headers,
        auth=(f"{task.host.username}", f"{task.host.password}"),
        verify=False,
    )
    task.host["ntp_facts"] = response.json()


def get_hub_spoke_dev_names():
    """
    Retrieve Device that are either DMVPN Hub or Spoke
    """
    devices = nr.filter(F(dmvpn="Hub") | F(dmvpn="Spoke")).inventory.hosts.keys()
    return devices


class TestNTPServersDMVPN:
    """
    Class to test Tunnel Status
    """

    @pytest.fixture(scope="class", autouse=True)
    def setup_teardown(self, pytestnr):
        """
        Setup and Teardown
        """
        pytestnr.inventory.defaults.username = os.getenv("USERNAME")
        pytestnr.inventory.defaults.password = os.getenv("PASSWORD")
        pytestnr_filtered = pytestnr.filter(F(dmvpn="Hub") | F(dmvpn="Spoke"))
        pytestnr_filtered.run(task=load_vars)
        pytestnr_filtered.run(task=get_ntp_servers)
        yield
        for host in pytestnr_filtered.inventory.hosts.values():
            host.data.pop("ntp_facts")

    @pytest.mark.parametrize("device_name", get_hub_spoke_dev_names())
    def test_ntp_server_state(self, pytestnr, device_name):
        """
        Parse NTP Servers
        Test Desired State
        """
        expected_list = []
        ntp_list = []

        nr_host = pytestnr.inventory.hosts[device_name]
        expected_ntp_servers = nr_host["loaded_vars"]["NTP"]
        for expected_ntp_server in expected_ntp_servers:
            expected_list.append(expected_ntp_server["server"])
        servers = nr_host["ntp_facts"]["Cisco-IOS-XE-native:ntp"]["Cisco-IOS-XE-ntp:server"]["server-list"]
        for server in servers:
            server_ip = server["ip-address"]
            ntp_list.append(server_ip)
        assert expected_list == ntp_list, f"{nr_host} FAILED"
