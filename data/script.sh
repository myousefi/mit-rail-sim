#!/bin/bash

input_file="blue_line_stations_qt.csv"
output_file="output.csv"

# Remove extra double quotes and modify station descriptive names based on given rules
awk -F, -v OFS="," '
NR==1 { print; next }
{
    gsub(/"/, "", $6)
    if ($6 ~ /\(Blue Line\)/) {
        sub(/ *\(Blue Line\)/, "", $6)
    } else if ($6 ~ /\(Blue, Brown, Green, Orange, Purple & Pink lines\)/) {
        sub(/ *\(Blue, Brown, Green, Orange, Purple & Pink lines\)/, "", $6)
    }
    print
}' "$input_file" > "$output_file"
