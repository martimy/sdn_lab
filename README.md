# SDN Lab

This repository contains the files and scripts for setting up a software-defined networking (SDN) lab using Mininet, Ryu controller, and FlowManager in Docker containers.

## Requirements

- A Linux-based operating system (tested on Ubuntu 20.04)
- Docker and docker-compose installed on your machine

## Usage

- Clone this repository to your local machine under folder 'sdn'
- Navigate to the root directory of the repository
- set env variable for flowmanager options `export FLOW_CMD='scripts/learning_switch_1.py`
- Run `docker compose up -d` to start the containers
- Run `docker exec -it sdn-mininet-1 bash` to enter the Mininet container
- Inside the container, run `./scripts/mn_oneswitch_topo.py to create a network topology
- Open a web browser and go to `http://localhost:8080/home/` to access the FlowManager web interface
- Use the web interface to view and manage the flows, switches, and links in the network
- To stop the containers, run `docker compose down` from the root directory of the repository

## License

This project is licensed under the MIT License - see the LICENSE file for details

