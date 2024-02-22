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
from ryu.lib.packet import ipv4
from ryu.lib.packet import tcp
from ryu.lib.packet import udp
from ryu.app.ofctl.api import get_datapath
from base_switch_dc import DCSwitch
from utils import Network

# Constants
ENTRY_TABLE = 0
LOCAL_TABLE = 0
REMOTE_TABLE = 1

MIN_PRIORITY = 0
LOW_PRIORITY = 100
MID_PRIORITY = 300


# Set idle_time=0 to make flow entries permenant
LONG_IDLE_TIME = 60
MID_IDLE_TIME = 40
IDLE_TIME = 30


class SpineLeaf2(DCSwitch):
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

        # Create a message to delete all exiting flows
        msgs = [self.del_flow(datapath)]

        # Set Match to ANY
        match = parser.OFPMatch()

        if datapath.id in net.leaves:  # For all leaf switches
            # Add a table-miss entry for LOCAL_TABLE:
            # Matched packets are sent to the next table
            inst = [parser.OFPInstructionGotoTable(REMOTE_TABLE)]
            msgs += [self.add_flow(datapath, LOCAL_TABLE, MIN_PRIORITY, match, inst)]

            # Add a table-miss entry for REMOTE_TABLE:
            # Matched packets are flooded and sent to the controller
            actions = [
                parser.OFPActionOutput(ofproto.OFPP_ALL),
                parser.OFPActionOutput(
                    ofproto.OFPP_CONTROLLER, ofproto.OFPCML_NO_BUFFER
                ),
            ]
            inst = [parser.OFPInstructionActions(ofproto.OFPIT_APPLY_ACTIONS, actions)]
            msgs += [self.add_flow(datapath, REMOTE_TABLE, MIN_PRIORITY, match, inst)]

        else:  # For all spine switches
            # Add a table-miss entry for ENTRY_TABLE to drop packets
            msgs += [self.add_flow(datapath, ENTRY_TABLE, MIN_PRIORITY, match, [])]

        # Send all messages to the switch
        self.send_messages(datapath, msgs)

    @set_ev_cls(ofp_event.EventOFPPacketIn, MAIN_DISPATCHER)
    def packet_in_handler(self, event):
        """Handle packet_in message.

        This method is called when a PacketIn message is received. The message
        is sent by the switch to request processing of the packet by the
        controller such as when a table miss occurs.
        """

        # Get switch and packet details
        datapath = event.msg.datapath
        ofproto = datapath.ofproto
        parser = datapath.ofproto_parser

        in_port = event.msg.match["in_port"]
        pkt = packet.Packet(event.msg.data)
        eth = pkt.get_protocol(ethernet.ethernet)

        # Ignore some packet types
        if eth.ethertype in self.ignore:
            return

        # Get the packet source and destination MAC addresses
        dst = eth.dst
        src = eth.src

        self.logger.info(
            f"PACKET IN from switch {datapath.id} port {in_port}, Details: src={src} dst={dst}"
        )

        # Get the packet higher layer information if available
        pkt_info = self.get_packet_info(pkt)
        self.logger.info(
            f"Packet Info: {pkt_info[0]}, {pkt_info[1]} - {pkt_info[2]}, {pkt_info[3]}"
        )

        # In the originating switch:

        # Add a flow entry in LOCAL_TABLE to forward packets to the given
        # output port if their destination MAC address matches the entry.
        match = parser.OFPMatch(eth_dst=src)
        actions = [parser.OFPActionOutput(in_port)]
        inst = [parser.OFPInstructionActions(ofproto.OFPIT_APPLY_ACTIONS, actions)]
        msgs = [
            self.add_flow(
                datapath, LOCAL_TABLE, LOW_PRIORITY, match, inst, i_time=LONG_IDLE_TIME
            )
        ]

        self.send_messages(datapath, msgs)

        self.update_mac_table(src, in_port, datapath.id)
        dst_host = self.mac_table.get(dst)
        remote_switches = list(set(net.leaves) - set([datapath.id]))

        if dst_host:
            # If the destination is in the MAC Table

            # If it is connected to a remote switch
            if dst_host["dpid"] in remote_switches:
                # Select a spine switch based on packet info
                # The selected spine must be the same in each direction
                IP_PACKET = all(pkt_info) # all items must be > 0
                spine_idx = (
                    self.select_spine_from_ip(pkt_info, len(net.spines))
                    if IP_PACKET
                    else self.select_spine_from_eth(src, dst, len(net.spines))
                )
                spine_id = net.spines[spine_idx]

                # In the originating switch,
                # add an entry to the REMOTE_TABLE to forward packets
                # from the source to the destination towards the spine switch

                # in_port = net.links[datapath.id, spine_id]["port"]
                upstream_port = net.links[datapath.id, spine_id]["port"]

                if IP_PACKET:
                    msgs = self.create_match_entry_for_ip_packet(
                        datapath,
                        REMOTE_TABLE,
                        MID_PRIORITY,
                        IDLE_TIME,
                        pkt_info,
                        upstream_port,
                    )
                else:
                    msgs = self.create_match_entry(
                        datapath,
                        REMOTE_TABLE,
                        LOW_PRIORITY,
                        IDLE_TIME,
                        src,
                        dst,
                        upstream_port,
                    )
                self.send_messages(datapath, msgs)

                # In the spine switch,
                # add two entries to forward packets between the source and
                # destination in both directions

                spine_datapath = get_datapath(self, spine_id)
                dst_datapath = get_datapath(self, dst_host["dpid"])
                spine_ingress_port = net.links[spine_id, datapath.id]["port"]
                spine_egress_port = net.links[spine_id, dst_datapath.id]["port"]

                if IP_PACKET:
                    msgs = self.make_dual_connections_for_ip_packet(
                        spine_datapath,
                        ENTRY_TABLE,
                        MID_PRIORITY,
                        pkt_info,
                        spine_ingress_port,
                        spine_egress_port,
                        MID_IDLE_TIME,
                    )                
                else:
                    msgs = self.make_dual_connections(
                        spine_datapath,
                        ENTRY_TABLE,
                        LOW_PRIORITY,
                        src,
                        dst,
                        spine_ingress_port,
                        spine_egress_port,
                        MID_IDLE_TIME,
                    )
                self.send_messages(spine_datapath, msgs)

                # In the remote switch,
                # Send the received packet to the destination switch
                # to forward it.
                remote_port = dst_host["port"]
                msgs = self.forward_packet(
                    dst_datapath, event.msg.data, ofproto.OFPP_CONTROLLER, remote_port
                )
                self.send_messages(dst_datapath, msgs)

        else:
            # If the destination is not in the MAC Table
            # Send the packet to all remote switches to be flooded
            for leaf in remote_switches:
                # Get the datapath object
                dpath = get_datapath(self, leaf)
                msgs = self.forward_packet(
                    dpath, event.msg.data, ofproto.OFPP_CONTROLLER, ofproto.OFPP_ALL
                )

                self.send_messages(dpath, msgs)

    def create_match_entry_for_ip_packet(
        self, datapath, table, priority, idle_time, packet_info, out_port
    ):
        ofproto = datapath.ofproto
        parser = datapath.ofproto_parser

        src_ip, src_port, dst_ip, dst_port = packet_info

        match = parser.OFPMatch(
            eth_type=0x0800,
            ipv4_src=src_ip,
            ipv4_dst=dst_ip,
            ip_proto=6,
            tcp_src=src_port,
            tcp_dst=dst_port,
        )
        actions = [parser.OFPActionOutput(out_port)]
        inst = [parser.OFPInstructionActions(ofproto.OFPIT_APPLY_ACTIONS, actions)]
        msg = [
            self.add_flow(
                datapath,
                table,
                priority,
                match,
                inst,
                i_time=idle_time,
            )
        ]

        return msg

    def create_match_entry(
        self, datapath, table, priority, idle_time, src, dst, out_port
    ):
        ofproto = datapath.ofproto
        parser = datapath.ofproto_parser

        match = parser.OFPMatch(eth_src=src, eth_dst=dst)
        actions = [parser.OFPActionOutput(out_port)]
        inst = [parser.OFPInstructionActions(ofproto.OFPIT_APPLY_ACTIONS, actions)]
        msg = [
            self.add_flow(
                datapath,
                table,
                priority,
                match,
                inst,
                i_time=idle_time,
            )
        ]

        return msg

    def make_dual_connections_for_ip_packet(
        self,
        datapath,
        table,
        priority,
        packet_info,
        in_port,
        out_port,
        i_time,
    ):
        """
        Returns MOD messages to add two flow entries allowing packets between
        two nodes
        """

        ofproto = datapath.ofproto
        parser = datapath.ofproto_parser

        src_ip, src_port, dst_ip, dst_port = packet_info


        match = parser.OFPMatch(
            in_port=in_port,
            eth_type=0x0800,
            ipv4_src=src_ip,
            ipv4_dst=dst_ip,
            ip_proto=6,
            tcp_src=src_port,
            tcp_dst=dst_port,
        )
        actions = [parser.OFPActionOutput(out_port)]
        inst = [parser.OFPInstructionActions(ofproto.OFPIT_APPLY_ACTIONS, actions)]
        msgs = [self.add_flow(datapath, table, priority, match, inst, i_time=i_time)]

        match = parser.OFPMatch(
            in_port=out_port,
            eth_type=0x0800,
            ipv4_src=dst_ip,
            ipv4_dst=src_ip,
            ip_proto=6,
            tcp_src=dst_port,
            tcp_dst=src_port,
        )
        actions = [parser.OFPActionOutput(in_port)]
        inst = [parser.OFPInstructionActions(ofproto.OFPIT_APPLY_ACTIONS, actions)]
        msgs += [self.add_flow(datapath, table, priority, match, inst, i_time=i_time)]
        return msgs
        
    def get_packet_info(self, pkt):
        """Get packet higher layer information"""

        ip_pkt = pkt.get_protocol(ipv4.ipv4)
        src_ip = ip_pkt.src if ip_pkt else 0
        dst_ip = ip_pkt.dst if ip_pkt else 0

        tcp_udp_pkt = pkt.get_protocol(tcp.tcp) or pkt.get_protocol(udp.udp)
        src_port = tcp_udp_pkt.src_port if tcp_udp_pkt else 0
        dst_port = tcp_udp_pkt.dst_port if tcp_udp_pkt else 0

        return src_ip, src_port, dst_ip, dst_port

    def select_spine_from_ip(self, packet_info, num_spines):
        """Select spine switch based source and destination IP addresses
        and TCP/UDP port numbers"""
        src_ip, src_port, dst_ip, dst_port = packet_info
        srcip_as_num = sum(map(int, src_ip.split(".")))
        dstip_as_num = sum(map(int, dst_ip.split(".")))
        return (srcip_as_num + dstip_as_num + src_port + dst_port) % num_spines

    def select_spine_from_eth(self, src, dst, num_spines):
        """Select spine switch based source and destination MAC addresses"""
        src_as_num = sum(map(int, src.split(":")))
        dst_as_num = sum(map(int, dst.split(":")))
        return (src_as_num + dst_as_num) % num_spines


config_file = os.environ.get("NETWORK_CONFIG_FILE", "network_config.yaml")
net = Network(config_file)
