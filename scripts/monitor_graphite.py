# Copyright (C) 2016 Nippon Telegraph and Telephone Corporation.
# Modifications copyright (C) 2024 Maen Artimy
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#    http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or
# implied.
# See the License for the specific language governing permissions and
# limitations under the License.

# Modified by Maen Artimy on 2024


import os
from operator import attrgetter
from ryu.app import simple_switch_13
from ryu.controller import ofp_event
from ryu.controller.handler import MAIN_DISPATCHER, DEAD_DISPATCHER
from ryu.controller.handler import set_ev_cls
from ryu.lib import hub
import graphyte


class SimpleMonitor13(simple_switch_13.SimpleSwitch13):

    def __init__(self, *args, **kwargs):
        super(SimpleMonitor13, self).__init__(*args, **kwargs)
        self.datapaths = {}
        self.monitor_thread = hub.spawn(self._monitor)
        self.setup_graphite()

    def setup_graphite(self):
        server = os.getenv('GRAPHITE_SERVER', '127.0.0.1')
        prefix = os.getenv('GRAPHITE_PREFIX', 'ryu.monitor')
        self.polltime = os.getenv('GRAPHITE_POLLTIME', 30)
        graphyte.init(server, prefix=prefix)

    @set_ev_cls(ofp_event.EventOFPStateChange, [MAIN_DISPATCHER, DEAD_DISPATCHER])
    def _state_change_handler(self, ev):
        datapath = ev.datapath
        if ev.state == MAIN_DISPATCHER:
            if datapath.id not in self.datapaths:
                self.logger.debug('register datapath: %016x', datapath.id)
                self.datapaths[datapath.id] = datapath
        elif ev.state == DEAD_DISPATCHER:
            if datapath.id in self.datapaths:
                self.logger.debug('unregister datapath: %016x', datapath.id)
                del self.datapaths[datapath.id]

    def _monitor(self):
        while True:
            for dp in self.datapaths.values():
                self._request_stats(dp)
            hub.sleep(self.polltime)

    def _request_stats(self, datapath):
        self.logger.debug('send stats request: %016x', datapath.id)
        ofproto = datapath.ofproto
        parser = datapath.ofproto_parser

        req = parser.OFPFlowStatsRequest(datapath)
        datapath.send_msg(req)

        req = parser.OFPPortStatsRequest(datapath, 0, ofproto.OFPP_ANY)
        datapath.send_msg(req)

    @set_ev_cls(ofp_event.EventOFPFlowStatsReply, MAIN_DISPATCHER)
    def _flow_stats_reply_handler(self, ev):
        body = ev.msg.body

        self.logger.info("Sending flow stats to Graphite")
        for stat in sorted([flow for flow in body if flow.priority == 1], key=lambda flow: (flow.match['in_port'], flow.match['eth_dst'])):
            # Send data to Graphite
            graphyte.send(f'{ev.msg.datapath.id}.flow.{stat.match["in_port"]}.{stat.match["eth_dst"]}.packets', stat.packet_count)
            graphyte.send(f'{ev.msg.datapath.id}.flow.{stat.match["in_port"]}.{stat.match["eth_dst"]}.bytes', stat.byte_count)

    @set_ev_cls(ofp_event.EventOFPPortStatsReply, MAIN_DISPATCHER)
    def _port_stats_reply_handler(self, ev):
        body = ev.msg.body

        self.logger.info("Sending port stats to Graphite")
        for stat in sorted(body, key=attrgetter('port_no')):
            # Send data to Graphite
            graphyte.send(f'{ev.msg.datapath.id}.port.{stat.port_no}.rx_packets', stat.rx_packets)
            graphyte.send(f'{ev.msg.datapath.id}.port.{stat.port_no}.rx_bytes', stat.rx_bytes)
            graphyte.send(f'{ev.msg.datapath.id}.port.{stat.port_no}.rx_errors', stat.rx_errors)
            graphyte.send(f'{ev.msg.datapath.id}.port.{stat.port_no}.tx_packets', stat.tx_packets)
            graphyte.send(f'{ev.msg.datapath.id}.port.{stat.port_no}.tx_bytes', stat.tx_bytes)
            graphyte.send(f'{ev.msg.datapath.id}.port.{stat.port_no}.tx_errors', stat.tx_errors)

