"""
Author: John McGovern (IPvZero)
"""
import os
import requests
import pytest
from nornir import InitNornir
from nornir.core.filter import F


nr = InitNornir(config_file="testconfig.yaml")


nr.inventory.defaults.username = os.getenv("USERNAME")
nr.inventory.defaults.password = os.getenv("PASSWORD")

headers = {
    "Accept": "application/yang-data+json",
}


def get_interfaces(task):
    """
    Retrieve Openconfig Interfaces
    """
    url = f"https://{task.host.hostname}:443/restconf/data/openconfig-interfaces:interfaces?content=nonconfig"
    response = requests.get(
        url=url,
        headers=headers,
        auth=(f"{task.host.username}", f"{task.host.password}"),
        verify=False,
    )
    task.host["intf_facts"] = response.json()


def get_hub_spoke_dev_names():
    """
    Retrieve Device that are either DMVPN Hub or Spoke
    """
    devices = nr.filter(F(dmvpn="Hub") | F(dmvpn="Spoke")).inventory.hosts.keys()
    return devices


class TestDMVPNTunnel:
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
        pytestnr_filtered.run(task=get_interfaces)
        yield
        for host in pytestnr_filtered.inventory.hosts.values():
            host.data.pop("intf_facts")

    @pytest.mark.parametrize("device_name", get_hub_spoke_dev_names())
    def test_tunnel_crypto(self, pytestnr, device_name):
        """
        Parse Interface Data
        Test Admin & Oper State is Up
        """
        nr_host = pytestnr.inventory.hosts[device_name]
        interfaces = nr_host["intf_facts"]["openconfig-interfaces:interfaces"][
            "interface"
        ]
        for interface in interfaces:
            if interface["name"] == "Tunnel0":
                admin_status = interface["state"]["admin-status"]
                oper_status = interface["state"]["oper-status"]
        assert admin_status == "UP", f"{nr_host} FAILED"
        assert oper_status == "UP", f"{nr_host} FAILED"
