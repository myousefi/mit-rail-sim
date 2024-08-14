import json

import pandas as pd

from mit_rail_sim.utils import project_root

# Read the Excel file
file_path = (
    project_root / "data" / "cta_blue_line_infra" / "BlueLine_Track_Circuit.xlsx"
)
df = pd.read_excel(file_path)

# Remove trailing 'T' from 'BLOCK' column
df["BLOCK"] = df["BLOCK"].str.replace("T$", "", regex=True)

df = df[df["DIRECTION"] == "Northbound"]
df = df[df["ROUTE"] == "OH_2"]

df.sort_values(by=["STARTSTN"], ascending=[True], inplace=True)

dict_df = df.to_dict(orient="records")
with open("output.json", "w") as f:
    json.dump(dict_df, f, indent=4)

# # Split the dataframe into two based on 'DIRECTION'
# df_southbound = df[df["DIRECTION"] == "Southbound"]
# df_northbound = df[df["DIRECTION"] == "Northbound"]

# # Define custom sort orders
# branch_order_northbound = ["CN", "DS", "LS", "OH"]
# branch_order_southbound = list(reversed(branch_order_northbound))

# # Set 'BRANCH' column to Categorical type with custom order
# df_southbound["BRANCH"] = pd.Categorical(
#     df_southbound["BRANCH"], categories=branch_order_southbound, ordered=True
# )
# df_northbound["BRANCH"] = pd.Categorical(
#     df_northbound["BRANCH"], categories=branch_order_northbound, ordered=True
# )

# # Sort each dataframe by 'BRANCH' and 'STARTSTN'
# df_southbound.sort_values(by=["BRANCH", "STARTSTN"], ascending=[True, True], inplace=True)
# df_northbound.sort_values(by=["BRANCH", "STARTSTN"], ascending=[True, False], inplace=True)

# # Convert rows to JSON
# json_list_southbound = df_southbound.to_dict(orient="records")
# json_list_northbound = df_northbound.to_dict(orient="records")

# # Write the list of JSON entries to a file
# with open("output_southbound.json", "w") as f:
#     json.dump(json_list_southbound, f, indent=4)

# with open("output_northbound.json", "w") as f:
#     json.dump(json_list_northbound, f, indent=4)
