#!/bin/bash

filename="/Users/moji/Projects/mit_rail_sim/test/output_files/passenger_test.csv"

echo "First 10 lines:"
echo "================"
head -n 10 $filename | column -t -s ","
echo ""
echo "Last 10 lines:"
echo "==============="
tail -n 10 $filename | column -t -s ","
