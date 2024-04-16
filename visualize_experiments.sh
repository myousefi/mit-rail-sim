#!/bin/bash

# Define the base command
BASE_CMD="python -m mit_rail_sim.dash_app.dash_app -r trb_experiments/"

# Start each app in the background
{ $BASE_CMD"FixedBlock/True/40/FB" | grep "^Dash is running on"; } &
{ $BASE_CMD"FixedBlock/False/40/FB" | grep "^Dash is running on"; } &
{ $BASE_CMD"FixedBlock/True/100/FB" | grep "^Dash is running on"; } &
{ $BASE_CMD"FixedBlock/False/100/FB" | grep "^Dash is running on"; } &
{ $BASE_CMD"MovingBlock/True/40/safety_margin_200" | grep "^Dash is running on"; } &
{ $BASE_CMD"MovingBlock/False/40/safety_margin_200" | grep "^Dash is running on"; } &
{ $BASE_CMD"MovingBlock/True/70/safety_margin_200" | grep "^Dash is running on"; } &
{ $BASE_CMD"MovingBlock/False/70/safety_margin_200" | grep "^Dash is running on"; } &

echo "Dash apps started in the background."
