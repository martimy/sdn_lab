# Copyright (c) 2024 Maen Artimy

from ryu.controller import ofp_event
from ryu.controller.handler import CONFIG_DISPATCHER, MAIN_DISPATCHER
from ryu.controller.handler import set_ev_cls
from ryu.ofproto import ofproto_v1_3
from ryu.lib.packet import packet
from ryu.lib.packet import ethernet
from ryu.lib.packet import ether_types
from ryu.app.ofctl.api import get_datapath
from base_switch import BaseSwitch


class DCSwitch(BaseSwitch):
    """Base data centre switch implementation that includes common funtcions"""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.mac_table = {}

        # Ignore these packet types
        self.ignore = [ether_types.ETH_TYPE_LLDP, ether_types.ETH_TYPE_IPV6]

    def update_mac_table(self, src, port, dpid):
        # Set/Update the node information in the MAC table
        # the MAC table includes the input port and input switch
        src_host = self.mac_table.get(src, {})
        src_host["port"] = port
        src_host["dpid"] = dpid
        self.mac_table[src] = src_host
        return src_host

    def make_dual_connections(
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
        Returns MOD messages to add two flow entries allowing packets between
        two nodes
        """

        ofproto = datapath.ofproto
        parser = datapath.ofproto_parser

        match = parser.OFPMatch(in_port=in_port, eth_src=src, eth_dst=dst)
        actions = [parser.OFPActionOutput(out_port)]
        inst = [parser.OFPInstructionActions(ofproto.OFPIT_APPLY_ACTIONS, actions)]
        msgs = [self.add_flow(datapath, table, priority, match, inst, i_time=i_time)]

        match = parser.OFPMatch(in_port=out_port, eth_src=dst, eth_dst=src)
        actions = [parser.OFPActionOutput(in_port)]
        inst = [parser.OFPInstructionActions(ofproto.OFPIT_APPLY_ACTIONS, actions)]
        msgs += [self.add_flow(datapath, table, priority, match, inst, i_time=i_time)]
        return msgs
