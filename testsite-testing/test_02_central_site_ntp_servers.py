"""
Author: John McGovern (IPvZero)
"""
import os
import pytest
from nornir import InitNornir
from nornir.core.filter import F
from nornir_scrapli.tasks import send_command
from nornir_utils.plugins.tasks.data import load_yaml

nr = InitNornir(config_file="testconfig.yaml")

nr.inventory.defaults.username = os.getenv("USERNAME")
nr.inventory.defaults.password = os.getenv("PASSWORD")


def get_ntp_servers(task):
    """
    Retrieve NTP Information as Structured Data
    """
    result = task.run(task=send_command, command="show ntp config")
    task.host["ntp_data"] = result.scrapli_response.genie_parse_output()


def load_vars(task):
    """
    Load Desired State
    """
    result = task.run(
        task=load_yaml, file=f"/home/ipvzero/Project/host_vars/{task.host}.yaml"
    )
    task.host["loaded_vars"] = result.result


def get_dev_names():
    """
    Identify Devices to Target
    """
    devices = nr.filter(F(site="central")).inventory.hosts.keys()
    return devices


class TestNTPServers:
    """
    Class to test NTP Servers
    """
    @pytest.fixture(scope="class", autouse=True)
    def setup_teardown(self, pytestnr):
        """
        Setup and Teardown
        """
        pytestnr.inventory.defaults.username = os.getenv("USERNAME")
        pytestnr.inventory.defaults.password = os.getenv("PASSWORD")
        pytestnr_filtered = pytestnr.filter(F(site="central"))
        pytestnr_filtered.run(load_vars)
        pytestnr_filtered.run(get_ntp_servers)
        yield
        for host in pytestnr_filtered.inventory.hosts.values():
            host.data.pop("ntp_data")

    @pytest.mark.parametrize("device_name", get_dev_names())
    def test_ntp_servers_are_consistent(self, pytestnr, device_name):
        """
        Test Live Network against Desired State
        """
        ntp_list = []
        expected_list = []
        nr_host = pytestnr.inventory.hosts[device_name]
        expected_ntp_servers = nr_host["loaded_vars"]["NTP"]
        for expected_ntp_server in expected_ntp_servers:
            expected_list.append(expected_ntp_server["server"])
        ntp_servers = nr_host["ntp_data"]["vrf"]["default"]["address"]
        for server in ntp_servers:
            ntp_list.append(server)
        assert expected_list == ntp_list, f"{nr_host} FAILED"
