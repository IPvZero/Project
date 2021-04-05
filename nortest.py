from nornir import InitNornir

nr = InitNornir(config_file="testconfig.yaml")

for host in nr.inventory.hosts:
    print(host)
