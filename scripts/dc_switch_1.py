"""
MIT License

Copyright (c) 2022-2024 Maen Artimy

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
from ryu.controller import ofp_event
from ryu.controller.handler import CONFIG_DISPATCHER, MAIN_DISPATCHER
from ryu.controller.handler import set_ev_cls
from ryu.ofproto import ofproto_v1_3
from ryu.lib.packet import packet
from ryu.lib.packet import ethernet
from ryu.lib.packet import ether_types
from ryu.app.ofctl.api import get_datapath
from base_switch import BaseSwitch
from utils import Network

# Constants
TABLE0 = 0
MIN_PRIORITY = 0
LOW_PRIORITY = 100

# Set idle_time=0 to make flow entries permenant
IDLE_TIME = 30


class SpineLeaf1(BaseSwitch):
    """
    A spine-leaf implementation with one table using static network description.
    """

    OFP_VERSIONS = [ofproto_v1_3.OFP_VERSION]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # Create central MAC table
        self.mac_table = {}

        # Ignore these packet types
        self.ignore = [ether_types.ETH_TYPE_LLDP, ether_types.ETH_TYPE_IPV6]

    @set_ev_cls(ofp_event.EventOFPSwitchFeatures, CONFIG_DISPATCHER)
    def switch_features_handler(self, event):
        """
        This method is called after the controller configures a switch.
        """

        datapath = event.msg.datapath
        ofproto = datapath.ofproto
        parser = datapath.ofproto_parser

        # Delete all exiting flows
        msgs = [self.del_flow(datapath)]

        if datapath.id in net.leaves:
            # Add a table-miss entry for TABLE0 table to forward
            # packets to the controller
            match = parser.OFPMatch()
            actions = [
                parser.OFPActionOutput(
                    ofproto.OFPP_CONTROLLER, ofproto.OFPCML_NO_BUFFER
                )
            ]
            inst = [parser.OFPInstructionActions(ofproto.OFPIT_APPLY_ACTIONS, actions)]

            msgs += [self.add_flow(datapath, TABLE0, MIN_PRIORITY, match, inst)]

        else:
            # Add a table-miss entry for TABLE0 table to drop packets
            match = parser.OFPMatch()
            inst = []

            msgs += [self.add_flow(datapath, TABLE0, MIN_PRIORITY, match, inst)]

        # Send all messages to the switch
        self.send_messages(datapath, msgs)

    @set_ev_cls(ofp_event.EventOFPPacketIn, MAIN_DISPATCHER)
    def packet_in_handler(self, event):
        """
        This method is called when a Packet-in message arrives from a swith.
        """

        datapath = event.msg.datapath
        ofproto = datapath.ofproto

        # Get the ingress port
        in_port = event.msg.match["in_port"]

        # Get the packet and its header
        pkt = packet.Packet(event.msg.data)
        eth = pkt.get_protocol(ethernet.ethernet)

        # Ignore some packets
        if eth.ethertype in self.ignore:
            return

        # Get the source and distanation MAC addresses
        dst = eth.dst
        src = eth.src

        self.logger.info("Packet from %i %s %s %i", datapath.id, src, dst, in_port)

        # Set/Update the node information in the MAC table
        # the MAC table includes the input port and input switch
        self.update_mac_table(src, in_port, datapath.id)
        dst_host = self.mac_table.get(dst)

        if dst_host:
            # Destination is known
            out_port = dst_host["port"]
            if dst_host["dpid"] == datapath.id:
                # Send this packet back to the switch to forward it.
                msgs = self.forward_packet(datapath, event.msg.data, in_port, out_port)

                # Both nodes are connected to the same leaf switch
                msgs += self.create_match_entry(
                    datapath,
                    TABLE0,
                    LOW_PRIORITY,
                    src,
                    dst,
                    in_port,
                    out_port,
                    IDLE_TIME,
                )
                self.send_messages(datapath, msgs)
            else:
                # Nodes reside on different leaf switches
                # Install flow entries in two leaf switches and one spine switch

                # Select one spine based on the src and dst switch IDs
                # The spine must be the same in both directions
                spine_id = net.spines[
                    (datapath.id + dst_host["dpid"]) % len(net.spines)
                ]

                # In the source switch
                upstream_port = net.links[datapath.id, spine_id]["port"]
                msgs = self.create_match_entry(
                    datapath,
                    TABLE0,
                    LOW_PRIORITY,
                    src,
                    dst,
                    in_port,
                    upstream_port,
                    IDLE_TIME,
                )

                self.send_messages(datapath, msgs)

                # In the spine switch
                spine_datapath = get_datapath(self, spine_id)
                dst_datapath = get_datapath(self, dst_host["dpid"])
                spine_ingress_port = net.links[spine_id, datapath.id]["port"]
                spine_egress_port = net.links[spine_id, dst_datapath.id]["port"]

                msgs = self.create_match_entry(
                    spine_datapath,
                    TABLE0,
                    LOW_PRIORITY,
                    src,
                    dst,
                    spine_ingress_port,
                    spine_egress_port,
                    IDLE_TIME,
                )
                self.send_messages(spine_datapath, msgs)

                # In the destination switch
                # Send this packet to the destination switch to forward it.
                remote_port = dst_host["port"]
                msgs = self.forward_packet(
                    dst_datapath, event.msg.data, ofproto.OFPP_CONTROLLER, remote_port
                )

                downstream_port = net.links[dst_datapath.id, spine_id]["port"]
                msgs += self.create_match_entry(
                    dst_datapath,
                    TABLE0,
                    LOW_PRIORITY,
                    src,
                    dst,
                    downstream_port,
                    remote_port,
                    IDLE_TIME,
                )
                self.send_messages(dst_datapath, msgs)
        else:
            # Destination is unknown, flood  the packet to all leaf switches
            for leaf in net.leaves:
                # Set the in_port to prevent sending pack the packet to the same port
                # in the source switch
                in_port = in_port if datapath.id == leaf else ofproto.OFPP_CONTROLLER
                # Get the datapath object
                dpath = get_datapath(self, leaf)
                # Send this packet to the switch to flood it.
                msgs = self.forward_packet(
                    dpath, event.msg.data, in_port, ofproto.OFPP_ALL
                )
                self.send_messages(dpath, msgs)

    def update_mac_table(self, src, port, dpid):
        # Set/Update the node information in the MAC table
        # the MAC table includes the input port and input switch
        src_host = self.mac_table.get(src, {})
        src_host["port"] = port
        src_host["dpid"] = dpid
        self.mac_table[src] = src_host
        return src_host

    def create_match_entry(
        self,
        datapath,
        table,
        priority,
        src,
        dst,
        in_port,
        out_port,
        i_time,
    ):
        """
        Returns MOD messages to a flow entry allowing packets between
        two nodes
        """

        ofproto = datapath.ofproto
        parser = datapath.ofproto_parser

        match = parser.OFPMatch(in_port=in_port, eth_src=src, eth_dst=dst)
        actions = [parser.OFPActionOutput(out_port)]
        inst = [parser.OFPInstructionActions(ofproto.OFPIT_APPLY_ACTIONS, actions)]
        msgs = [self.add_flow(datapath, table, priority, match, inst, i_time=i_time)]

        return msgs


config_file = os.environ.get("NETWORK_CONFIG_FILE", "network_config.yaml")
net = Network(config_file)
