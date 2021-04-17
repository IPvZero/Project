"""
AUTHOR: John McGovern (IPvZero)
      
"""
import os
import sys
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

config_file = sys.argv[1]
nr = InitNornir(config_file=config_file)

nr.inventory.defaults.username = os.getenv("USERNAME")
nr.inventory.defaults.password = os.getenv("PASSWORD")


def load_vars(task):
    """
    Load host variables and bind them to a per-host dict key called "facts"
    Load group variables and bind them to a dict key called "group_facts"
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


def config_ntp(task):
    """
    Build NTP config based on IOS-XR YANG Model
    Push configuration over NETCONF
    """

    ntp_template = task.run(
        task=template_file,
        name="Buildling NTP Configuration",
        template="netconf-ntp.j2",
        path="./templates",
    )
    ntp_output = ntp_template.result
    task.run(
        task=netconf_edit_config,
        name="Automating NTP",
        target="candidate",
        config=ntp_output,
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


ntp_results = targets.run(task=config_ntp)
print_result(ntp_results)

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
