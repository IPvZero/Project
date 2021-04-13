"""
Author: John McGovern (IPvZero)
"""
import os
import requests
import pytest
from nornir import InitNornir
from nornir.core.filter import F


nr = InitNornir(config_file="prodconfig.yaml")


nr.inventory.defaults.username = os.getenv("USERNAME")
nr.inventory.defaults.password = os.getenv("PASSWORD")

headers = {
    "Accept": "application/yang-data+json",
}


def get_cryptography(task):
    """
    Retrieve Tunnel Crypto Data
    """
    url = f"https://{task.host.hostname}:443/restconf/data/crypto-oper-data"
    response = requests.get(
        url=url,
        headers=headers,
        auth=(f"{task.host.username}", f"{task.host.password}"),
        verify=False,
    )
    task.host["crypto_facts"] = response.json()


def get_hub_spoke_dev_names():
    """
    Retrieve Device that are either DMVPN Hub or Spoke
    """
    devices = nr.filter(F(dmvpn="Hub") | F(dmvpn="Spoke")).inventory.hosts.keys()
    return devices


class TestDMVPNCryptography:
    """
    Class to test Tunnel Cryptography
    """

    @pytest.fixture(scope="class", autouse=True)
    def setup_teardown(self, pytestnr):
        """
        Setup and Teardown
        """
        pytestnr.inventory.defaults.username = os.getenv("USERNAME")
        pytestnr.inventory.defaults.password = os.getenv("PASSWORD")
        pytestnr_filtered = pytestnr.filter(F(dmvpn="Hub") | F(dmvpn="Spoke"))
        pytestnr_filtered.run(task=get_cryptography)
        yield
        for host in pytestnr_filtered.inventory.hosts.values():
            host.data.pop("crypto_facts")

    @pytest.mark.parametrize("device_name", get_hub_spoke_dev_names())
    def test_tunnel_crypto(self, pytestnr, device_name):
        """
        Parse Crypto Data
        Test State is Active
        """
        nr_host = pytestnr.inventory.hosts[device_name]
        inbound_status = nr_host["crypto_facts"][
            "Cisco-IOS-XE-crypto-oper:crypto-oper-data"
        ]["crypto-ipsec-ident"][0]["ident-data"]["inbound-esp-sa"]["sa-status"]
        outbound_status = nr_host["crypto_facts"][
            "Cisco-IOS-XE-crypto-oper:crypto-oper-data"
        ]["crypto-ipsec-ident"][0]["ident-data"]["outbound-esp-sa"]["sa-status"]
        assert inbound_status == "crypto-sa-status-active", f"{nr_host} FAILED"
        assert outbound_status == "crypto-sa-status-active", f"{nr_host} FAILED"
