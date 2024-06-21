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

from ryu.base import app_manager
from ryu.controller import ofp_event
from ryu.controller.handler import CONFIG_DISPATCHER, MAIN_DISPATCHER
from ryu.controller.handler import set_ev_cls
from ryu.ofproto import ofproto_v1_3
from ryu.lib.packet import packet
from ryu.lib.packet import ethernet
from ryu.lib.packet import ether_types
from base_switch import BaseSwitch

# Constants
LEARN_TABLE = 0
FORWARD_TABLE = 1

LOW_PRIORITY = 0
MID_PRIORITY = 100
TOP_PRIORITY = 300


class LearningSwitch2(BaseSwitch):
    """
    A L2 switch implementation with two tables.
    """

    OFP_VERSIONS = [ofproto_v1_3.OFP_VERSION]

    def __init__(self, *args, **kwargs):
        super(LearningSwitch2, self).__init__(*args, **kwargs)

    # Event Handlers

    @set_ev_cls(ofp_event.EventOFPSwitchFeatures, CONFIG_DISPATCHER)
    def switch_features_handler(self, ev):
        """
        Handle switch features reply message.

        This method is called when features-reply message is received at the
        end of the configuration phase.

        The controller clear all existing flow entries and installs table-miss
        flow entries in each table.
        """

        datapath = ev.msg.datapath
        ofproto = datapath.ofproto
        parser = datapath.ofproto_parser

        # Delete all exiting flows
        msgs = [self.del_flow(datapath)]

        # Create table-miss flow entry for LEARN_TABLE
        # Copies of matched packets are forwarded to the controller and also
        # forwarded to the next table
        match = parser.OFPMatch()
        actions = [
            parser.OFPActionOutput(ofproto.OFPP_CONTROLLER, ofproto.OFPCML_NO_BUFFER)
        ]
        inst = [
            parser.OFPInstructionActions(ofproto.OFPIT_APPLY_ACTIONS, actions),
            parser.OFPInstructionGotoTable(FORWARD_TABLE),
        ]

        msgs += [self.add_flow(datapath, LEARN_TABLE, LOW_PRIORITY, match, inst)]

        # Create table-miss flow entry for FORWARD_TABLE
        # Matched packets are flooded
        match = parser.OFPMatch()
        actions = [parser.OFPActionOutput(ofproto.OFPP_FLOOD)]
        inst = [parser.OFPInstructionActions(ofproto.OFPIT_APPLY_ACTIONS, actions)]

        msgs += [self.add_flow(datapath, FORWARD_TABLE, LOW_PRIORITY, match, inst)]

        # Send all messages to the switch
        self.send_messages(datapath, msgs)

    @set_ev_cls(ofp_event.EventOFPPacketIn, MAIN_DISPATCHER)
    def packet_in_handler(self, ev):
        """Handle packet_in message.

        This method is called when a PacketIn message is received. The message
        is sent by the switch to request processing of the packet by the
        controller such as when a table miss occurs.
        """

        datapath = ev.msg.datapath
        ofproto = datapath.ofproto
        parser = datapath.ofproto_parser

        in_port = ev.msg.match["in_port"]
        pkt = packet.Packet(ev.msg.data)
        eth = pkt.get_protocol(ethernet.ethernet)

        # Ignore LLDP packets
        if eth.ethertype == ether_types.ETH_TYPE_LLDP:
            return

        dst = eth.dst
        src = eth.src

        self.logger.info("packet in %s %s %s %s", datapath.id, src, dst, in_port)

        # Install a flow entry in LEARN_TABLE to forward packets to FORWARD_TABLE
        # if their input port and source MAC address match the entry
        match = parser.OFPMatch(in_port=in_port, eth_src=src)
        inst = [parser.OFPInstructionGotoTable(FORWARD_TABLE)]
        msgs = [
            self.add_flow(datapath, LEARN_TABLE, MID_PRIORITY, match, inst, i_time=30)
        ]

        # Install a flow entry in FORWARD_TABLE to forward packets to the given
        # output port if their destination MAC address matches the entry.
        match = parser.OFPMatch(eth_dst=src)
        actions = [parser.OFPActionOutput(in_port)]
        inst = [parser.OFPInstructionActions(ofproto.OFPIT_APPLY_ACTIONS, actions)]
        msgs += [
            self.add_flow(datapath, FORWARD_TABLE, MID_PRIORITY, match, inst, i_time=40)
        ]

        self.send_messages(datapath, msgs)
