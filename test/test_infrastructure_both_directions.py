import json
import unittest
from io import StringIO
from unittest.mock import patch

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots

FIGURE_WIDTH = 10000
FIGURE_HEIGHT = 1000
MARGIN = dict(l=50, r=50, b=100, t=100, pad=4)

INFRA_FILE_NAME = "inputs/infra.json"


class TestPlotInfrastructureBothDirections(unittest.TestCase):
    def setUp(self):
        try:
            with open(INFRA_FILE_NAME) as f:
                data = json.load(f)

            self.rail_data_json = data
        except FileNotFoundError:
            print(f"File {INFRA_FILE_NAME} not found.")
            return []
        except json.JSONDecodeError:
            print(f"Error decoding JSON from file {INFRA_FILE_NAME}")
            return []

    def test_plot_infrastructure(self):
        for dir in ["Northbound", "Southbound"]:
            rail_data = self.rail_data_json[dir]

            print(f"Plotting {dir} rail data...")
            print("_______________________________________________________________")
            for idx in range(len(rail_data) - 1):
                block = rail_data[idx]
                next_block = rail_data[idx + 1]

                if abs(block["STARTSTN"] - block["ENDSTN"]) != block["DISTANCE"]:
                    print(f"Block {block['BLOCK']} has inconsistent distance.")
