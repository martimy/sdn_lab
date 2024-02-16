import yaml
from mininet.net import Mininet
from mininet.node import RemoteController
from mininet.node import OVSSwitch
from mininet.node import Host
from mininet.link import TCLink
from mininet.log import setLogLevel
from mininet.log import info
from mininet.cli import CLI

def create_mininet_network(config_file):
    with open(config_file, "r") as file:
        config = yaml.safe_load(file)

    net = Mininet(controller=RemoteController, link=TCLink, switch=OVSSwitch)

    info("*** Adding controller\n")
    c0 = net.addController(
        "ctrl", controller=RemoteController, ip="127.0.0.1", port=6633
    )

    switches = {}
    hosts = {}

    info("*** Adding switches\n")
    for switch_config in config["switches"]:
        switch = net.addSwitch(switch_config)
        switches[switch_config] = switch
        # switch = net.addSwitch(switch_config["name"])
        # switches[switch_config["name"]] = switch

    info("*** Adding hosts\n")
    for host_config in config["hosts"]:
        host = net.addHost(
            host_config["name"],
            ip=host_config["ip"],
            mac=host_config["mac"],
            defaultRoute=host_config["default_route"],
        )
        hosts[host_config["name"]] = host
        switch = switches[host_config["connected_to"]]
        port = host_config["port"]
        net.addLink(host, switch, port1=port)

    info("*** Adding links\n")
    for link_config in config["links"]:
        source_switch = switches[link_config["source"]]
        target_switch = switches[link_config["target"]]
        net.addLink(
            source_switch,
            target_switch,
            port1=link_config["source_port"],
            port2=link_config["target_port"],
        )

    info("*** Starting network\n")
    net.build()
    info("*** Starting controllers\n")
    c0.start()
    info("*** Starting switches\n")
    for switch in switches.values():
        switch.start([c0])

    CLI(net)

    info("*** Stopping network\n")
    net.stop()


if __name__ == "__main__":
    setLogLevel("info")
    create_mininet_network("network_config.yaml")
