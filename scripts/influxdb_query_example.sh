#!/bin/bash

curl -G http://localhost:8086/query \
     --data-urlencode "db=ryu_monitor" \
     --data-urlencode "q=SELECT * FROM port_stats" \
     --header "Accept: application/csv"
