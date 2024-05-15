import pandas as pd

# Convert the CSV data into a DataFrame
df = pd.read_csv("../data/cta_afc_data_for_load_flow_pre_rebuild.csv")

# Convert transaction_dtm to datetime, extract time component, and determine the day type
df["transaction_dtm"] = pd.to_datetime(df["transaction_dtm"])
df["time"] = df["transaction_dtm"].dt.hour
df["day_type"] = df["transaction_dtm"].dt.dayofweek.apply(
    lambda x: "Weekday" if x < 5 else "Saturday" if x == 5 else "Sunday"
)

# Define columns to fill
fill_columns = [
    "route_sequence",
    "direction_sequence",
    "boarding_platform_sequence",
    "alighting_platform_sequence",
    "first_route",
    "first_direction",
    "first_boarding_platform",
    "first_alighting_platform",
]


# Function to impute missing data within each group
def impute_within_group(group):
    non_nan_rows = group.dropna(subset=fill_columns)
    if non_nan_rows.empty:
        # If there are no rows to impute from, return the group as is
        return group

    # for col in fill_columns:
    # For rows with NaN in the current column, fill them with values from a randomly chosen row
    nan_rows = group[fill_columns].isna().any(axis=1)
    group.loc[nan_rows, fill_columns] = (
        non_nan_rows[fill_columns].sample(n=nan_rows.sum(), replace=True).values
    )

    return group


# Apply the imputation function to each group
df = (
    df.groupby(["boarding_stop", "time", "day_type"])
    .apply(impute_within_group)
    .reset_index(drop=True)
)

# Save the imputed data
df.to_csv("../data/cta_afc_data_for_load_flow_imputed_pre_rebuild.csv", index=False)
