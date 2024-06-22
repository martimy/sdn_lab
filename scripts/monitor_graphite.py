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
from operator import attrgetter
from ryu.base import app_manager
from ryu.controller import ofp_event
from ryu.controller.handler import MAIN_DISPATCHER, DEAD_DISPATCHER
from ryu.controller.handler import set_ev_cls
from ryu.ofproto import ofproto_v1_3
from base_switch import BaseSwitch
from ryu.lib import hub
import graphyte


class MonitorGraphite(BaseSwitch):
    """
    Sending network stats to Graphite
    """

    OFP_VERSIONS = [ofproto_v1_3.OFP_VERSION]

    def __init__(self, *args, **kwargs):
        super(MonitorGraphite, self).__init__(*args, **kwargs)
        self.setup_graphite()
        self.datapaths = {}
        self.monitor_thread = hub.spawn(self._monitor)

    def setup_graphite(self):
        """Setup Graphite server"""

        server = os.getenv("GRAPHITE_SERVER", "127.0.0.1")
        prefix = os.getenv("GRAPHITE_PREFIX", "ryu.monitor")
        polltime_str = os.getenv("GRAPHITE_POLLTIME", "10.0")
        self.polltime = float(polltime_str)
        graphyte.init(server, prefix=prefix)
        self.logger.info(
            f"Sending telemetry '{prefix}' to server '{server}' every {self.polltime} sec."
        )

    def _monitor(self):
        """
        Continue polling the switches.
        """
        while True:
            for dp in self.datapaths.values():
                self._request_stats(dp)
            hub.sleep(self.polltime)

    def _request_stats(self, datapath):
        self.logger.debug("send stats request: %016x", datapath.id)
        ofproto = datapath.ofproto
        parser = datapath.ofproto_parser

        msgs = [parser.OFPFlowStatsRequest(datapath)]
        msgs += [parser.OFPPortStatsRequest(datapath, 0, ofproto.OFPP_ANY)]

        self.send_messages(datapath, msgs)

    # Event Handlers

    @set_ev_cls(ofp_event.EventOFPStateChange, [MAIN_DISPATCHER, DEAD_DISPATCHER])
    def _state_change_handler(self, ev):
        """Add or remove datapaths"""

        datapath = ev.datapath
        if ev.state == MAIN_DISPATCHER:
            if datapath.id not in self.datapaths:
                self.logger.info("register datapath: %016x", datapath.id)
                self.datapaths[datapath.id] = datapath
        elif ev.state == DEAD_DISPATCHER:
            if datapath.id in self.datapaths:
                self.logger.info("unregister datapath: %016x", datapath.id)
                del self.datapaths[datapath.id]

    @set_ev_cls(ofp_event.EventOFPFlowStatsReply, MAIN_DISPATCHER)
    def _flow_stats_reply_handler(self, ev):
        """
        Receive flow stats.
        The flows are filtered so only flows from entries that have 'eth_dst' match are
        reported. Change the filtering criteria to get the desired stats.
        """

        body = ev.msg.body

        self.logger.info(f"Sending flow stats from {ev.msg.datapath.id} to Graphite")
        for stat in sorted(
            [flow for flow in body if flow.match.get("eth_dst")],
            key=lambda flow: (flow.table_id, flow.match["eth_dst"]),
        ):
            # Send data to Graphite
            graphyte.send(
                f'{ev.msg.datapath.id}.flow.{stat.table_id}.{stat.match["eth_dst"]}.packets',
                stat.packet_count,
            )
            graphyte.send(
                f'{ev.msg.datapath.id}.flow.{stat.table_id}.{stat.match["eth_dst"]}.bytes',
                stat.byte_count,
            )

    @set_ev_cls(ofp_event.EventOFPPortStatsReply, MAIN_DISPATCHER)
    def _port_stats_reply_handler(self, ev):
        """REceive port stats"""

        body = ev.msg.body

        self.logger.info(f"Sending port stats from {ev.msg.datapath.id} to Graphite")
        for stat in sorted(body, key=attrgetter("port_no")):
            # Send data to Graphite
            graphyte.send(
                f"{ev.msg.datapath.id}.port.{stat.port_no}.rx_packets", stat.rx_packets
            )
            graphyte.send(
                f"{ev.msg.datapath.id}.port.{stat.port_no}.rx_bytes", stat.rx_bytes
            )
            graphyte.send(
                f"{ev.msg.datapath.id}.port.{stat.port_no}.rx_errors", stat.rx_errors
            )
            graphyte.send(
                f"{ev.msg.datapath.id}.port.{stat.port_no}.tx_packets", stat.tx_packets
            )
            graphyte.send(
                f"{ev.msg.datapath.id}.port.{stat.port_no}.tx_bytes", stat.tx_bytes
            )
            graphyte.send(
                f"{ev.msg.datapath.id}.port.{stat.port_no}.tx_errors", stat.tx_errors
            )
