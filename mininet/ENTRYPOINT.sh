#!/usr/bin/env bash

# Start the Open vSwitch service
service openvswitch-switch start

# Set the Open vSwitch manager to listen on port 6640 for OpenFlow connections
#ovs-vsctl set-manager ptcp:6640

# Check if any arguments were passed to the script
if [ $# -gt 0 ]
then
  # If the first argument is "mn", execute the arguments passed to the script in a new Bash shell
  if [ "$1" == "mn" ]
  then
    bash -c "$@"
  else
    # If the first argument is not "mn", execute the Mininet (mn) command with the arguments passed to the script
    mn "$@"
  fi
else
  # If no arguments were passed to the script, start a new Bash shell
  bash
fi

# Stop the Open vSwitch service
service openvswitch-switch stop

