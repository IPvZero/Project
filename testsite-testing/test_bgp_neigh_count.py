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


def get_bgp_neighbor_count(task):
    """
    Retrieve BGP State Data
    """
    url = f"https://{task.host.hostname}:443/restconf/data/bgp-state-data"
    response = requests.get(
        url=url,
        headers=headers,
        auth=(f"{task.host.username}", f"{task.host.password}"),
        verify=False,
    )
    task.host["bgp_facts"] = response.json()


def get_hub_spoke_dev_names():
    """
    Retrieve Device that are either DMVPN Hub or Spoke
    """
    devices = nr.filter(F(dmvpn="Hub") | F(dmvpn="Spoke")).inventory.hosts.keys()
    return devices


class TestDMVPNBGPNeighbors:
    """
    Class to test BGP
    """

    NEIGHBOR_COUNT = {"Hub": 3, "Spoke": 1}

    @pytest.fixture(scope="class", autouse=True)
    def setup_teardown(self, pytestnr):
        """
        Setup and Teardown
        """
        pytestnr.inventory.defaults.username = os.getenv("USERNAME")
        pytestnr.inventory.defaults.password = os.getenv("PASSWORD")
        pytestnr_filtered = pytestnr.filter(F(dmvpn="Hub") | F(dmvpn="Spoke"))
        pytestnr_filtered.run(task=get_bgp_neighbor_count)
        yield
        for host in pytestnr_filtered.inventory.hosts.values():
            host.data.pop("bgp_facts")

    @pytest.mark.parametrize("device_name", get_hub_spoke_dev_names())
    def test_bgp_neighbor_count(self, pytestnr, device_name):
        """
        Parse BGP neighbor IDs
        Append to List
        Test length of List
        """
        nr_host = pytestnr.inventory.hosts[device_name]
        neighbor_list = []
        dmvpn_role = nr_host["dmvpn"]
        if dmvpn_role == "Spoke":
            bgp_neighbors = nr_host["bgp_facts"][
                "Cisco-IOS-XE-bgp-oper:bgp-state-data"
            ]["neighbors"]["neighbor"]
            for neighbor in bgp_neighbors:
                neighbor_id = neighbor["neighbor-id"]
                neighbor_list.append(neighbor_id)
        elif dmvpn_role == "Hub":
            bgp_neighbors = nr_host["bgp_facts"][
                "Cisco-IOS-XE-bgp-oper:bgp-state-data"
            ]["address-families"]["address-family"][0]["bgp-neighbor-summaries"][
                "bgp-neighbor-summary"
            ]
            for neighbor in bgp_neighbors:
                neighbor_id = neighbor["id"]
                neighbor_list.append(neighbor_id)
        num_neighbors = len(neighbor_list)
        expected_neighbors = TestBGPNeighbors.NEIGHBOR_COUNT[dmvpn_role]
        assert num_neighbors == expected_neighbors, f"{nr_host} FAILED"
