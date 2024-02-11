#!/bin/sh

# Check if any arguments are provided
if [ $# -eq 0 ]; then
  # Execute the default command without options
  exec ryu-manager flowmanager/flowmanager.py
else
  if [ "$1" = "ryu-manager" ]; then
    # Execute the provided command and arguments
    # shift 1  # Remove the first argument, which is "ryu-manager"
    exec ryu-manager "$@"
  else
    # Execute the default command with provided options
    exec ryu-manager flowmanager/flowmanager.py "$@"
  fi
fi

