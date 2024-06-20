#!/usr/bin/python3

"""
MIT License

Copyright (c) 2018-2024 Maen Artimy

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
from mininet.net import Mininet
from mininet.node import RemoteController
from mininet.node import OVSSwitch
from mininet.node import Host
from mininet.link import TCLink
from mininet.log import setLogLevel
from mininet.log import info
from mininet.cli import CLI


def labBaseNetwork(ctrl="127.0.0.1"):
    "Network Topology of one switch and two hosts using mid-level API."

    net = Mininet(controller=RemoteController, link=TCLink, switch=OVSSwitch)
    info("*** Adding controller\n")
    c0 = net.addController("c0", controller=RemoteController, ip=ctrl, port=6633)

    info("*** Adding switches\n")
    s1 = net.addSwitch("S691201")

    info("*** Adding hosts\n")
    h1 = net.addHost(
        "h1",
        cls=Host,
        mac="00:00:00:00:00:01",
        ip="10.1.1.10",
        defaultRoute="via 10.1.1.1",
    )
    h2 = net.addHost(
        "h2",
        cls=Host,
        mac="00:00:00:00:00:02",
        ip="10.1.1.20",
        defaultRoute="via 10.1.1.1",
    )

    info("*** Adding links\n")
    net.addLink(h1, s1)
    net.addLink(h2, s1)

    info("*** Starting network\n")
    net.build()

    info("*** Starting controllers\n")
    c0.start()

    info("*** Starting switches\n")
    s1.start([c0])

    CLI(net)

    info("*** Stopping network")
    net.stop()


if __name__ == "__main__":
    # run using:
    # sudo /path/mn_switch_topo.py

    setLogLevel("info")
    ctrl_address = os.getenv("SDN_CONTROLLER", "127.0.0.1")

    # Get the controller address. This overrides the env variable
    if len(sys.argv) > 1:
        ctrl_address = sys.argv[1]

    labBaseNetwork(ctrl=ctrl_address)
