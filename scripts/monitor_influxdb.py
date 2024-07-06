import os
from operator import attrgetter
from ryu.base import app_manager
from ryu.controller import ofp_event
from ryu.controller.handler import MAIN_DISPATCHER, DEAD_DISPATCHER
from ryu.controller.handler import set_ev_cls
from ryu.ofproto import ofproto_v1_3
from base_switch import BaseSwitch
from ryu.lib import hub
from influxdb import InfluxDBClient


class MonitorInfluxDB(BaseSwitch):
    """
    Sending network stats to InfluxDB
    """

    OFP_VERSIONS = [ofproto_v1_3.OFP_VERSION]

    def __init__(self, *args, **kwargs):
        super(MonitorInfluxDB, self).__init__(*args, **kwargs)
        self.setup_influxdb()
        self.datapaths = {}
        self.monitor_thread = hub.spawn(self._monitor)

    def setup_influxdb(self):
        """Setup InfluxDB client"""

        self.influx_client = InfluxDBClient(
            host=os.getenv("INFLUXDB_HOST", "127.0.0.1"),
            port=int(os.getenv("INFLUXDB_PORT", "8086")),
            username=os.getenv("INFLUXDB_USER", "root"),
            password=os.getenv("INFLUXDB_PASSWORD", "root"),
        )
        self.polltime = float(os.getenv("INFLUXDB_POLLTIME", "10.0"))
        self.logger.info(
            f"Sending telemetry to InfluxDB at {self.influx_client._baseurl} every {self.polltime} sec."
        )

        database = os.getenv("INFLUXDB_DB", "ryu_monitor")
        names = [item["name"] for item in self.influx_client.get_list_database()]
        if database not in names:
            self.influx_client.create_database(database)

        self.influx_client.switch_database(database)

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

    def _has_controller_action(self, stat, ofproto):
        for instruction in stat.instructions:
            if instruction.type == ofproto.OFPIT_APPLY_ACTIONS:
                for action in instruction.actions:
                    if action.type == ofproto.OFPAT_OUTPUT and action.port == ofproto.OFPP_CONTROLLER:
                        return True
        return False

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

        for stat in body:
            if self._has_controller_action(stat, ev.msg.datapath.ofproto):
                # Send data to InfluxDB
                data = [
                    {
                        "measurement": "flow_stats",
                        "tags": {
                            "datapath": ev.msg.datapath.id,
                            "table_id": stat.table_id,
                            "dest": "controller",
                        },
                        "fields": {"packets": stat.packet_count, "bytes": stat.byte_count},
                    }
                ]
                self.influx_client.write_points(data)


        self.logger.info(f"Sending flow stats from {ev.msg.datapath.id} to InfluxDB")
        for stat in sorted(
            [flow for flow in body if flow.match.get("eth_dst")],
            key=lambda flow: (flow.table_id, flow.match["eth_dst"]),
        ):
            # Send data to InfluxDB
            data = [
                {
                    "measurement": "flow_stats",
                    "tags": {
                        "datapath": ev.msg.datapath.id,
                        "table_id": stat.table_id,
                        "eth_dst": stat.match["eth_dst"],
                    },
                    "fields": {"packets": stat.packet_count, "bytes": stat.byte_count},
                }
            ]
            self.influx_client.write_points(data)

    @set_ev_cls(ofp_event.EventOFPPortStatsReply, MAIN_DISPATCHER)
    def _port_stats_reply_handler(self, ev):
        """Receive port stats"""

        body = ev.msg.body

        self.logger.info(f"Sending port stats from {ev.msg.datapath.id} to InfluxDB")
        for stat in sorted(body, key=attrgetter("port_no")):
            # Send data to InfluxDB
            data = [
                {
                    "measurement": "port_stats",
                    "tags": {"datapath": ev.msg.datapath.id, "port_no": stat.port_no},
                    "fields": {
                        "rx_packets": stat.rx_packets,
                        "rx_bytes": stat.rx_bytes,
                        "rx_errors": stat.rx_errors,
                        "tx_packets": stat.tx_packets,
                        "tx_bytes": stat.tx_bytes,
                        "tx_errors": stat.tx_errors,
                    },
                }
            ]
            self.influx_client.write_points(data)
