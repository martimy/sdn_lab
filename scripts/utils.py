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
