from mininet.net import Mininet
from mininet.log import setLogLevel, info
import time

setLogLevel('info')

# Set parameters
duration = 60
streams = 4
bandwidth = 10

# Get hosts
host_names = ['h1', 'h2', 'h3', 'h4']

hosts = []
for h in host_names:
  hosts.append(net.get(h))

server = hosts[3]

# Start iperf3 server on h4
info('*** Starting iperf3 server on h4\n')
server.cmd('iperf3 -s &')

# Start iperf3 clients on h1, h2, and h3 to send traffic to h4
info('*** Starting iperf3 clients on h1, h2, and h3\n')
for h in hosts:
  h.cmd(f'iperf3 -c {server.IP()} -t {duration} -i 10 -P {streams} -b {bandwidth}M -M 1400 > /dev/null 2>&1 &')

# Wait for the tests to complete
info('*** Waiting for iperf3 tests to complete\n')

# Sleep for the duration of the test
time.sleep(duration + 2)

# Print output from h4
info(server.cmd('pkill iperf3'))

#info('*** Starting the second round\n')
net.iperf(hosts=[h1,h2,h3,h4], seconds=30, port=5001)
