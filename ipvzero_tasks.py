"""
AUTHOR: John McGovern (IPvZero)
"""

import logging
import re
import os
import sys
from datetime import datetime
from nornir import InitNornir
from nornir.core.filter import F
from nornir_napalm.plugins.tasks import napalm_get
from nornir_jinja2.plugins.tasks import template_file
from nornir_utils.plugins.tasks.data import load_yaml

config_file = sys.argv[1]
nr = InitNornir(config_file=config_file)

targets = nr.filter(F(site="central"))
targets.inventory.defaults.username = os.getenv("USERNAME")
targets.inventory.defaults.password = os.getenv("PASSWORD")

etx = chr(3)
time = datetime.now().strftime("%H-%M-%S")


def replace_ospf(task):
    """
    Task to Pull Running Config
    Use Regex to Insert New Configurations
    """
    data = task.run(
        task=load_yaml,
        file=f"./host_vars/{task.host}.yaml",
        severity_level=logging.DEBUG,
    )
    task.host["facts"] = data.result
    config = task.run(task=napalm_get, getters=["config"], severity_level=logging.DEBUG)
    showrun = config.result["config"]["running"]
    pattern = re.compile("^router ospf([^!]+)", flags=re.I | re.M)
    routing_template = task.run(
        task=template_file,
        name="Buildling Routing Configuration",
        template="ospf.j2",
        path="./templates",
        severity_level=logging.DEBUG,
    )
    template_to_load = routing_template.result
    newconfig = re.sub(pattern, template_to_load, showrun)
    final_config = newconfig.replace("^C", etx)
    return final_config


def replace_vlan(task):
    """
    Task to Pull Running Config
    Use Regex to Insert New Configurations
    """
    data = task.run(
        task=load_yaml,
        file=f"./host_vars/{task.host}.yaml",
        severity_level=logging.DEBUG,
    )
    task.host["facts"] = data.result
    config = task.run(task=napalm_get, getters=["config"], severity_level=logging.DEBUG)
    showrun = config.result["config"]["running"]
    pattern = re.compile("!\n!", flags=re.I | re.M)
    newchar = "`"
    newconfig = re.sub(pattern, newchar, showrun)
    vlanpattern = re.compile("vlan[^`]+", flags=re.I | re.M)
    load_template = task.run(
        task=template_file,
        name="Buildling Routing Configuration",
        template="vlan.j2",
        path="./templates",
        severity_level=logging.DEBUG,
    )
    vlan_template = load_template.result
    vlan_config = re.sub(vlanpattern, vlan_template, newconfig)
    configuration = vlan_config.replace("`", "!")
    final_config = configuration.replace("^C", etx)
    return final_config


def replace_ntp(task):
    """
    Task to Pull Running Config
    Use Regex to Insert New NTP Configurations
    """
    data = task.run(
        task=load_yaml,
        file=f"./host_vars/{task.host}.yaml",
        severity_level=logging.DEBUG,
    )
    task.host["facts"] = data.result
    config = task.run(task=napalm_get, getters=["config"], severity_level=logging.DEBUG)
    showrun = config.result["config"]["running"]
    pattern = re.compile("^ntp([^!]+)", flags=re.I | re.M)
    routing_template = task.run(
        task=template_file,
        name="Buildling Routing Configuration",
        template="ntp.j2",
        path="./templates",
        severity_level=logging.DEBUG,
    )
    template_to_load = routing_template.result
    newconfig = re.sub(pattern, template_to_load, showrun)
    final_config = newconfig.replace("^C", etx)
    return final_config
