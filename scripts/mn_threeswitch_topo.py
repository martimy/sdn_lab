#!/usr/bin/python3

# Copyright (C) 2018 Maen Artimy

from mininet.net import Mininet
from mininet.node import RemoteController
from mininet.node import OVSSwitch
from mininet.node import Host
from mininet.link import TCLink
from mininet.log import setLogLevel
from mininet.log import info
from mininet.cli import CLI


def labBaseNetwork():
    "Network Topology of 3 switches and four hosts using mid-level API."

    net = Mininet(controller=RemoteController, link=TCLink, switch=OVSSwitch)
    info('*** Adding controller\n')
    c0 = net.addController('c0',
                           controller=RemoteController,
                           ip='127.0.0.1',
                           port=6633)

    info('*** Adding switches\n')
    s1 = net.addSwitch('SW1')
    s2 = net.addSwitch('SW2')
    s3 = net.addSwitch('SW3')

    info('*** Adding hosts\n')
    h1 = net.addHost('h1', cls=Host, mac="00:00:00:00:00:01",
                     ip='10.1.1.10',  defaultRoute='via 10.1.1.1')
    h2 = net.addHost('h2', cls=Host, mac="00:00:00:00:00:02",
                     ip='10.1.1.20',  defaultRoute='via 10.1.1.1')
    h3 = net.addHost('h3', cls=Host, mac="00:00:00:00:00:03",
                     ip='10.1.1.30',  defaultRoute='via 10.1.1.1')
    h4 = net.addHost('h4', cls=Host, mac="00:00:00:00:00:04",
                     ip='10.1.1.40',  defaultRoute='via 10.1.1.1')

    info('*** Adding links\n')
    net.addLink(s2, h1, 1)
    net.addLink(s2, h2, 2)
    net.addLink(s2, s1, 3, 1)
    net.addLink(s3, h3, 1)
    net.addLink(s3, h4, 2)
    net.addLink(s3, s1, 3, 2)

    info('*** Starting network\n')
    net.build()

    info('*** Starting controllers\n')
    c0.start()

    info('*** Starting switches\n')
    s1.start([c0])
    s2.start([c0])
    s3.start([c0])

    CLI(net)

    info('*** Stopping network')
    net.stop()


if __name__ == '__main__':
    # run using:
    # sudo /path/mn_switch_topo.py

    setLogLevel('info')
    labBaseNetwork()
