#!/usr/bin/python3

"""
MIT License

Copyright (c) 2024 Maen Artimy

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.
"""

import os
import sys
import yaml
from mininet.net import Mininet
from mininet.node import RemoteController
from mininet.node import OVSSwitch
from mininet.node import Host
from mininet.link import TCLink
from mininet.log import setLogLevel
from mininet.log import info
from mininet.cli import CLI


def create_mininet_network(config_file, ctrl="127.0.0.1"):
    with open(config_file, "r") as file:
        config = yaml.safe_load(file)

    net = Mininet(controller=RemoteController, link=TCLink, switch=OVSSwitch)

    info("*** Adding controller\n")
    c0 = net.addController("ctrl", controller=RemoteController, ip=ctrl, port=6633)

    switches = {}
    hosts = {}

    info("*** Adding switches\n")
    for switch_config in config["switches"]:
        switches[switch_config["name"]] = net.addSwitch(switch_config["name"])

    info("*** Adding inter-switch links\n")
    for link_config in config["links"]:
        source_switch = switches[link_config["source"]]
        target_switch = switches[link_config["target"]]
        net.addLink(
            source_switch,
            target_switch,
            port1=link_config["source_port"],
            port2=link_config["target_port"],
        )

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
    ctrl_address = os.getenv("SDN_CONTROLLER", "127.0.0.1")

    # Check if the command-line argument is provided
    if len(sys.argv) < 2:
        print(
            "Usage: sudo ./path/mn_spineleaf_topo.py <netconfig_file> [controller_address]"
        )
        sys.exit(1)

    config_file = sys.argv[1]  # Get the config file name from the command-line argument

    # Get the controller address. This overrides the env. variable
    if len(sys.argv) > 2:
        ctrl_address = sys.argv[2]

    setLogLevel("info")
    create_mininet_network(config_file, ctrl_address)
