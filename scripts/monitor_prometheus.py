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
from ryu.app.wsgi import ControllerBase, WSGIApplication, route
from ryu.base import app_manager
from ryu.controller import ofp_event
from ryu.controller.handler import MAIN_DISPATCHER, DEAD_DISPATCHER
from ryu.controller.handler import set_ev_cls
from ryu.lib import hub
from ryu.ofproto import ofproto_v1_3
from webob import Response
from prometheus_client import CollectorRegistry, Gauge, generate_latest
from prometheus_client.core import REGISTRY

# URL for Prometheus metrics endpoint
PROMETHEUS_ENDPOINT = "/metrics"


class MonitorPrometheus(app_manager.RyuApp):
    """Ryu application that initializes Prometheus metrics and handles packet-in events."""

    _CONTEXTS = {"wsgi": WSGIApplication}

    def __init__(self, *args, **kwargs):
        super(MonitorPrometheus, self).__init__(*args, **kwargs)

        wsgi = kwargs["wsgi"]
        wsgi.register(PrometheusController, {MonitorPrometheus.__name__: self})

        self.datapaths = {}
        self.monitor_thread = hub.spawn(self._monitor)

        self.polltime = float(os.getenv("PROMETHEUS_POLLTIME", "10.0"))

        # Prometheus metrics
        self.flow_count_gauge = Gauge(
            "ryu_flow_count", "Flows count", ["datapath_id", "table_id"]
        )
        self.packet_count_gauge = Gauge(
            "ryu_packet_count",
            "Packet count per flow",
            ["datapath_id", "table_id", "eth_dst", "ipv4_dst", "ipv4_src"],
        )
        self.byte_count_gauge = Gauge(
            "ryu_byte_count",
            "Byte count per flow",
            ["datapath_id", "table_id", "eth_dst", "ipv4_dst", "ipv4_src"],
        )
        # self.duration_sec_gauge = Gauge(
        #     "ryu_duration_sec",
        #     "Flow duration in seconds",
        #     ["datapath_id", "table_id", "eth_dst", "ipv4_dst", "ipv4_src"])

    @set_ev_cls(ofp_event.EventOFPStateChange, [MAIN_DISPATCHER, DEAD_DISPATCHER])
    def _state_change_handler(self, ev):
        datapath = ev.datapath
        if ev.state == MAIN_DISPATCHER:
            self.datapaths[datapath.id] = datapath
        elif ev.state == DEAD_DISPATCHER:
            if datapath.id in self.datapaths:
                del self.datapaths[datapath.id]

    def _monitor(self):
        while True:
            for dp in self.datapaths.values():
                self._request_stats(dp)
            hub.sleep(self.polltime)

    def _request_stats(self, datapath):
        self.logger.debug("send stats request: %016x", datapath.id)
        ofproto = datapath.ofproto
        parser = datapath.ofproto_parser

        req = parser.OFPFlowStatsRequest(datapath)
        datapath.send_msg(req)

    @set_ev_cls(ofp_event.EventOFPFlowStatsReply, MAIN_DISPATCHER)
    def _flow_stats_reply_handler(self, ev):
        body = ev.msg.body

        # Get flow count per table
        table_flow_count = {}
        for stat in body:
            table_id = stat.table_id
            x = table_flow_count.setdefault(table_id, 0)
            table_flow_count[table_id] = x + 1

        for table_id, count in table_flow_count.items():
            self.flow_count_gauge.labels(
                datapath_id=ev.msg.datapath.id, table_id=table_id
            ).set(count)

        # Get all flows with ANY in the Match field
        for stat in [flow for flow in body if not flow.match]:
            self.packet_count_gauge.labels(
                datapath_id=ev.msg.datapath.id,
                table_id=stat.table_id,
                eth_dst="",
                ipv4_dst="",
                ipv4_src="",
            ).set(stat.packet_count)
            self.byte_count_gauge.labels(
                datapath_id=ev.msg.datapath.id,
                table_id=stat.table_id,
                eth_dst="",
                ipv4_dst="",
                ipv4_src="",
            ).set(stat.byte_count)
            # self.duration_sec_gauge.labels(
            #     datapath_id=ev.msg.datapath.id,
            #     table_id=stat.table_id,
            #     eth_dst="",
            #     ipv4_dst="",
            #     ipv4_src="",
            # ).set(stat.duration_sec)

        # Get all flows with 'eth_dst' in the Match field
        for stat in sorted(
            [flow for flow in body if flow.match.get("eth_dst")],
            key=lambda flow: (flow.table_id, flow.match["eth_dst"]),
        ):
            flow_id = f"{stat.table_id}_{stat.match['eth_dst']}"
            self.packet_count_gauge.labels(
                datapath_id=ev.msg.datapath.id,
                table_id=stat.table_id,
                eth_dst=stat.match["eth_dst"],
                ipv4_dst="",
                ipv4_src="",
            ).set(stat.packet_count)
            self.byte_count_gauge.labels(
                datapath_id=ev.msg.datapath.id,
                table_id=stat.table_id,
                eth_dst=stat.match["eth_dst"],
                ipv4_dst="",
                ipv4_src="",
            ).set(stat.byte_count)
            # self.duration_sec_gauge.labels(
            #     datapath_id=ev.msg.datapath.id,
            #     table_id=stat.table_id,
            #     eth_dst=stat.match["eth_dst"],
            #     ipv4_dst="",
            #     ipv4_src="",
            # ).set(stat.duration_sec)

        # Get all flows with 'ipv4_dst' in the Match field
        for stat in sorted(
            [flow for flow in body if flow.match.get("ipv4_dst")],
            key=lambda flow: (
                flow.table_id,
                flow.match["ipv4_dst"],
                flow.match["ipv4_src"],
            ),
        ):
            flow_id = (
                f"{stat.table_id}_{stat.match['ipv4_dst']}_{stat.match['ipv4_src']}"
            )
            self.packet_count_gauge.labels(
                datapath_id=ev.msg.datapath.id,
                table_id=stat.table_id,
                eth_dst="",
                ipv4_dst=stat.match["ipv4_dst"],
                ipv4_src=stat.match["ipv4_src"],
            ).set(stat.packet_count)
            self.byte_count_gauge.labels(
                datapath_id=ev.msg.datapath.id,
                table_id=stat.table_id,
                eth_dst="",
                ipv4_dst=stat.match["ipv4_dst"],
                ipv4_src=stat.match["ipv4_src"],
            ).set(stat.byte_count)
            # self.duration_sec_gauge.labels(
            #     datapath_id=ev.msg.datapath.id,
            #     table_id=stat.table_id,
            #     eth_dst="",
            #     ipv4_dst=stat.match["ipv4_dst"],
            #     ipv4_src=stat.match["ipv4_src"],
            # ).set(stat.duration_sec)


class PrometheusController(ControllerBase):
    """WSGI controller that serves the Prometheus metrics endpoint."""

    def __init__(self, req, link, data, **config):
        super(PrometheusController, self).__init__(req, link, data, **config)
        self.simple_monitor_app = data[MonitorPrometheus.__name__]

    @route("prometheus", PROMETHEUS_ENDPOINT, methods=["GET"])
    def metrics(self, req, **kwargs):
        registry = CollectorRegistry()
        # Collect default and custom metrics
        collectors = REGISTRY._collector_to_names.keys()
        print(collectors)
        for collector in collectors:
            registry.register(collector)

        data = generate_latest(registry)
        return Response(content_type="text/plain", body=data)
