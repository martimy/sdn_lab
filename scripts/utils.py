# Copyright (c) 2024 Maen Artimy

import yaml
import sys


class Network:
    """
    Network definition
    """

    def __init__(self, config_file):
        try:
            with open(config_file, "r") as file:
                config = yaml.safe_load(file)
        except FileNotFoundError:
            print(f"Error: Config file '{config_file}' not found.")
            sys.exit(1)

        self.spines = [
            s["id"] for s in config["switches"] if s["type"].lower() == "spine"
        ]
        self.leaves = [
            s["id"] for s in config["switches"] if s["type"].lower() == "leaf"
        ]

        switch_mapping = {switch["name"]: switch["id"] for switch in config["switches"]}

        self.links = {}
        for link in config["links"]:
            if link["source"] in switch_mapping and link["target"] in switch_mapping:
                self.links[
                    (switch_mapping[link["source"]], switch_mapping[link["target"]])
                ] = {
                    "port": link["source_port"],
                }
                self.links[
                    (switch_mapping[link["target"]], switch_mapping[link["source"]])
                ] = {
                    "port": link["target_port"],
                }
