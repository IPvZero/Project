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


def get_vlans(task):
    """
    Retrieve VLAN Information as Structured Data
    """
    result = task.run(task=send_command, command="show vlan")
    task.host["vlan_data"] = result.scrapli_response.genie_parse_output()


def load_vars(task):
    """
    Load VLAN Desired State
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


class TestVLANs:
    """
    Class to test VLANs
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
        pytestnr_filtered.run(get_vlans)
        yield
        for host in pytestnr_filtered.inventory.hosts.values():
            host.data.pop("vlan_data")

    @pytest.mark.parametrize("device_name", get_dev_names())
    def test_vlans_for_consistency(self, pytestnr, device_name):
        """
        Test Live Network against Desired State
        """
        vlan_list = []
        nr_host = pytestnr.inventory.hosts[device_name]
        expected_vlans = nr_host["loaded_vars"]["VLANS"]
        vlans = nr_host["vlan_data"]["vlans"]
        for vlan in vlans:
            if vlan in ["1", "1002", "1003", "1004", "1005"]:
                continue
            vlan_id = int(vlan)
            name = vlans[vlan]["name"]
            vlan_dict = {"id": vlan_id, "name": name}
            vlan_list.append(vlan_dict)
        assert expected_vlans == vlan_list, f"{nr_host} FAILED"
