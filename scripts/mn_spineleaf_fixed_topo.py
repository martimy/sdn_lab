#!/usr/bin/python3


# Copyright (c) 2018-2022 Maen Artimy


from mininet.net import Mininet
from mininet.node import RemoteController
from mininet.node import OVSSwitch
from mininet.node import Host
from mininet.link import TCLink
from mininet.log import setLogLevel
from mininet.log import info
from mininet.cli import CLI


def create_mininet_network():
    """
    Create Mininet network topology of three leaf switches, two spine switches
    and six hosts.
    """

    info("*** Create a network with OVS switches")
    net = Mininet(controller=RemoteController, link=TCLink, switch=OVSSwitch)
    info("*** Adding controller\n")
    c0 = net.addController(
        "ctrl", controller=RemoteController, ip="127.0.0.1", port=6633
    )

    info("*** Adding switches\n")
    s11 = net.addSwitch("SW11")  # Spine
    s12 = net.addSwitch("SW12")  # Spine
    s21 = net.addSwitch("SW21")  # Leaf
    s22 = net.addSwitch("SW22")  # Leaf
    s23 = net.addSwitch("SW23")  # Leaf

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

    h3 = net.addHost(
        "h3",
        cls=Host,
        mac="00:00:00:00:00:03",
        ip="10.1.1.30",
        defaultRoute="via 10.1.1.1",
    )

    h4 = net.addHost(
        "h4",
        cls=Host,
        mac="00:00:00:00:00:04",
        ip="10.1.1.40",
        defaultRoute="via 10.1.1.1",
    )

    h5 = net.addHost(
        "h5",
        cls=Host,
        mac="00:00:00:00:00:05",
        ip="10.1.1.50",
        defaultRoute="via 10.1.1.1",
    )

    h6 = net.addHost(
        "h6",
        cls=Host,
        mac="00:00:00:00:00:06",
        ip="10.1.1.60",
        defaultRoute="via 10.1.1.1",
    )

    info("*** Adding links\n")
    net.addLink(s11, s21, 1, 1)
    net.addLink(s11, s22, 2, 1)
    net.addLink(s11, s23, 3, 1)
    net.addLink(s12, s21, 1, 2)
    net.addLink(s12, s22, 2, 2)
    net.addLink(s12, s23, 3, 2)
    net.addLink(s21, h1, 3)
    net.addLink(s21, h2, 4)
    net.addLink(s22, h3, 3)
    net.addLink(s22, h4, 4)
    net.addLink(s23, h5, 3)
    net.addLink(s23, h6, 4)

    info("*** Starting network\n")
    net.build()
    info("*** Starting controllers\n")
    c0.start()
    info("*** Starting switches\n")
    s11.start([c0])
    s12.start([c0])
    s21.start([c0])
    s22.start([c0])
    s23.start([c0])

    CLI(net)

    info("*** Stopping network")
    net.stop()


if __name__ == "__main__":
    # run using:
    # sudo /path/mn_spineleaf_topo.py

    setLogLevel("info")
    create_mininet_network()
