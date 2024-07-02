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

from mininet.net import Mininet
from mininet.log import setLogLevel, info
import time

setLogLevel("info")

# Set parameters
duration = 60
streams = 4
bandwidth = 100  # Kbps

# Get hosts
host_names = ["h1", "h2", "h3", "h4", "h5", "h6"]

hosts = []
for h in host_names:
    hosts.append(net.get(h))

server = hosts[3]

# Start iperf3 server on h4
info("*** Starting iperf3 server\n")
server.cmd("iperf3 -s &")

# Start iperf3 clients on h1, h2, and h3 to send traffic to h4
info("*** Starting iperf3 clients\n")
for h in hosts:
    if h is not server:
        h.cmd(
            f"iperf3 -c {server.IP()} -t {duration} -i 10 -P {streams} -b {bandwidth}K -M 1400 > /dev/null 2>&1 &"
        )

# Wait for the tests to complete
info("*** Waiting for iperf3 tests to complete\n")

# Sleep for the duration of the test
time.sleep(duration + 2)

# Print output from h4
info(server.cmd("pkill iperf3"))
