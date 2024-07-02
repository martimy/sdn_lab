# SDN Lab

This repository provides a software-defined networking (SDN) lab environment using [Mininet](https://mininet.org/), [Ryu](https://ryu-sdn.org/) controller, and [FlowManager](https://github.com/martimy/flowmanager) in [Docker](https://www.docker.com/) containers. The repository also includes Python applications to forward network traffic among hosts in spine-leaf data centre topology. Another set of applications are available to collect traffic metrics from the switches and send them to three common time-series database (Graphite, Prometheus, and InfluxDB). The network stats can be viewed using Grafana.

This lab provides an example of running multiple SDN applications in a network. Each application handle a single task:

- `flowmanager.py`: views the network topology and flow tables for all switches. It also allows manual manipulation of the flow tables.
- `dc_switch_1.py`, `dc_switch_2.py`, and `dc_switch_3.py`: create flow entries to forward packtes among the hosts in the network across the spine-leaf topology in a manner that balances the load among the spine routers using different techniques.
- `monitor_graphite.py`, `monitor_prometheus.py`, and `monitor_influxd.py`: collect network stats from swiches and send the to the corrosponding database.


## Requirements

- A Linux-based operating system (tested on Ubuntu 20.04)
- Docker and docker-compose installed on your machine


## Instructions


For instructions on how to use repo for basic SDN oprtaions, consult the [lab instructions](docs/lab_instructions.md). To add network monitoring capabilties, consult the [monitoring instructions](docs/monitoring.md).

