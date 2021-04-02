"""
AUTHOR: John McGovern (IPvZero)
      
"""
import os
from nornir import InitNornir
from nornir.core.exceptions import NornirExecutionError
from nornir.core.filter import F
from nornir_utils.plugins.tasks.data import load_yaml
from nornir_utils.plugins.functions import print_result
from nornir_jinja2.plugins.tasks import template_file
from nornir_scrapli.tasks import (
    netconf_edit_config,
    netconf_commit,
    netconf_lock,
    netconf_unlock,
    netconf_discard,
    netconf_validate,
)

nr = InitNornir(config_file="config.yaml")

nr.inventory.defaults.username = os.getenv("USERNAME")
nr.inventory.defaults.password = os.getenv("PASSWORD")


def load_vars(task):
    """
    Load host variables and bind them to a per-host dict key called "facts"
    """

    data = task.run(
        task=load_yaml,
        name="Loading Vars Into Memory...",
        file=f"./host_vars/{task.host}.yaml",
    )
    group_data = task.run(task=load_yaml, file="./group_vars/all.yaml")
    task.host["facts"] = data.result
    task.host["group_facts"] = group_data.result


def lock_config(task):
    """
    Lock Candidate Datastore
    """
    task.run(task=netconf_lock, target="candidate", name="Locking...")


def config_bgp(task):
    """
    Build BGP config based on IOS-XR YANG Model
    Push configuration over NETCONF
    """
    templatepath = task.host.data["dmvpn"]
    bgp_template = task.run(
        task=template_file,
        name="Buildling BGP Configuration",
        template=f"{templatepath}.j2",
        path="./templates/bgp/",
    )
    bgp_output = bgp_template.result
    task.run(
        task=netconf_edit_config,
        name="Automating BGP",
        target="candidate",
        config=bgp_output,
    )


def tunnel(task):
    """
    Build Tunnel/Crypto config based on IOS-XR YANG Model
    Push configuration over NETCONF
    """
    tunnelpath = task.host.data["dmvpn"]
    tunnel_template = task.run(
        task=template_file,
        name="Buildling Tunnel Configuration",
        template=f"{tunnelpath}.j2",
        path="./templates/dmvpn/tunnel/",
    )
    tunnel_output = tunnel_template.result
    task.run(
        task=netconf_edit_config,
        name="Automating Tunnel Creation",
        target="candidate",
        config=tunnel_output,
    )


def vrf(task):
    """
    Build VRF config based on IOS-XR YANG Model
    Push configuration over NETCONF
    """

    vrf_template = task.run(
        task=template_file,
        name="Buildling VRF Configuration",
        template="vrf.j2",
        path="./templates/",
    )
    vrf_output = vrf_template.result
    task.run(
        task=netconf_edit_config,
        name="Automating VRF",
        target="candidate",
        config=vrf_output,
    )


def validate_configs(task):
    """
    Validate Candidate Configuration
    """
    task.run(task=netconf_validate, source="candidate")


def commit_configs(task):
    """
    Commit the configuration changes into Running Datastore
    """
    task.run(
        task=netconf_commit, name="Committing Changes into the Running Configuration"
    )


def discard_all(task):
    """
    Discard all candidate configurations
    """
    task.run(task=netconf_discard)


def unlock_config(task):
    """
    Unlock Candidate datastore
    """
    task.run(task=netconf_unlock, target="candidate")


targets = nr.filter(F(dmvpn="Hub") | F(dmvpn="Spoke"))
var_result = targets.run(task=load_vars)
print_result(var_result)

lock_result = targets.run(task=lock_config, name="NETCONF_LOCK")
print_result(lock_result)

vrf_results = targets.run(task=vrf)
print_result(vrf_results)

bgp_results = targets.run(task=config_bgp)
print_result(bgp_results)

tunnel_results = targets.run(task=tunnel)
print_result(tunnel_results)

validate_results = targets.run(task=validate_configs)
print_result(validate_results)

failures = targets.data.failed_hosts
if failures:
    undo_all = targets.run(task=discard_all)
    print_result(undo_all)
else:
    commits = targets.run(task=commit_configs)
    print_result(commits)

unlocker = targets.run(task=unlock_config, name="NETCONF_UNLOCK")
print_result(unlocker)

if failures:
    raise NornirExecutionError("Nornir Failure Detected")
