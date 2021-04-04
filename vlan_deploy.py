"""
Author: John McGovern (IPvZero)
"""
import os
import sys
from nornir import InitNornir
from nornir.core.filter import F
from nornir_utils.plugins.functions import print_result
from nornir_napalm.plugins.tasks import napalm_configure
from ipvzero_tasks import replace_vlan

config_file = sys.argv[1]
nr = InitNornir(config_file=config_file)
targets = nr.filter(F(site="central"))

targets.inventory.defaults.username = os.getenv("USERNAME")
targets.inventory.defaults.password = os.getenv("PASSWORD")


def replace_feature(task):
    """
    Load in custom IPvZero task
    Replace VLAN Configuration
    """

    config = replace_vlan(task)
    task.run(task=napalm_configure, configuration=config, replace=True)


result = targets.run(task=replace_feature)
print_result(result)
