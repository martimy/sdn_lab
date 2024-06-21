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
TABLE0 = 0
LOW_PRIORITY = 0
MID_PRIORITY = 100


class LearningSwitch1(BaseSwitch):
    """
    A L2 switch implementation with one table
    """

    OFP_VERSIONS = [ofproto_v1_3.OFP_VERSION]

    def __init__(self, *args, **kwargs):
        super(LearningSwitch1, self).__init__(*args, **kwargs)
        self.mac_to_port = {}

    @set_ev_cls(ofp_event.EventOFPSwitchFeatures, CONFIG_DISPATCHER)
    def switch_features_handler(self, ev):
        """
        This method is called after the controller configures a switch.
        """
        datapath = ev.msg.datapath
        ofproto = datapath.ofproto
        parser = datapath.ofproto_parser

        # Create message to delete all exiting flow entries in the switch
        msgs = [self.del_flow(datapath)]

        # Create message to add a table-miss entry for TABLE0 table
        match = parser.OFPMatch()
        actions = [
            parser.OFPActionOutput(ofproto.OFPP_CONTROLLER, ofproto.OFPCML_NO_BUFFER)
        ]
        inst = [parser.OFPInstructionActions(ofproto.OFPIT_APPLY_ACTIONS, actions)]

        msgs += [self.add_flow(datapath, TABLE0, LOW_PRIORITY, match, inst)]

        # Send all messages to the switch
        self.send_messages(datapath, msgs)

    @set_ev_cls(ofp_event.EventOFPPacketIn, MAIN_DISPATCHER)
    def packet_in_handler(self, ev):
        """
        This method is called when a Packet-in message arrives from a swith.
        """
        datapath = ev.msg.datapath
        ofproto = datapath.ofproto
        parser = datapath.ofproto_parser

        # Get the ingress port
        in_port = ev.msg.match["in_port"]

        # Get the packet and its header
        pkt = packet.Packet(ev.msg.data)
        eth = pkt.get_protocol(ethernet.ethernet)

        # Ignore LLDP packets
        if eth.ethertype == ether_types.ETH_TYPE_LLDP:
            return

        # Get the source and distanation MAC addresses
        dst = eth.dst
        src = eth.src

        self.logger.info("packet in %s %s %s %s", datapath.id, src, dst, in_port)

        # Create a MAC table for the switch if none exists.
        mac_table = self.mac_to_port.setdefault(datapath.id, {})

        # Learn the MAC address
        mac_table[src] = in_port

        # The out_port will be the learned port of or FLOOD the packets
        out_port = mac_table.get(dst, ofproto.OFPP_FLOOD)

        actions = [parser.OFPActionOutput(out_port)]

        # Create a message to install a flow entry to forward future packets
        # from learned hosts.
        msgs = []
        if out_port != ofproto.OFPP_FLOOD:
            match = parser.OFPMatch(in_port=in_port, eth_src=src, eth_dst=dst)
            actions = [parser.OFPActionOutput(out_port)]
            inst = [parser.OFPInstructionActions(ofproto.OFPIT_APPLY_ACTIONS, actions)]
            msgs = [
                self.add_flow(datapath, TABLE0, MID_PRIORITY, match, inst, i_time=0)
            ]

        # Send this packet back to the switch to forward it.
        actions = [parser.OFPActionOutput(out_port)]
        msgs += [
            parser.OFPPacketOut(
                datapath=datapath,
                buffer_id=ofproto.OFP_NO_BUFFER,
                in_port=in_port,
                actions=actions,
                data=ev.msg.data,
            )
        ]

        self.send_messages(datapath, msgs)
