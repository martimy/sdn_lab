# SDN Lab

This repository contains the files and scripts for setting up a software-defined networking (SDN) lab using [Mininet](https://mininet.org/), [Ryu](https://ryu-sdn.org/) controller, and [FlowManager](https://github.com/martimy/flowmanager) in [Docker](https://www.docker.com/) containers.

## Requirements

- A Linux-based operating system (tested on Ubuntu 20.04)
- Docker and docker-compose installed on your machine

## Usage

- Clone this repository to your local machine under folder 'sdn'
- Navigate to the root directory of the repository
- Run `docker compose up -d` to start the containers
- Open a web browser and go to `http://localhost:8080/home/` to access the FlowManager web interface
- To stop the containers, run `docker compose down` from the root directory of the repository

```bash
$ git clone https://github.com/martimy/sdn_lab sdn
$ cd sdn
sdn$ docker compose up -d
...
sdn$ docker compose down
```

For complete lab instructions consult this [document](lab_instructions.md).

## License

This project is licensed under the MIT License - see the LICENSE file for details

