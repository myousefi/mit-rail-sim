# %%
import pandas as pd
import plotly.graph_objects as go
import json
from mit_rail_sim.utils import project_root
import plotly.io as pio

pio.templates.default = "simple_white"


def load_and_process_data(file_path):
    with open(file_path, "r") as file:
        data = json.load(file)
    df = pd.DataFrame(data["empirical_schedule"])
    df["time_of_day"] = pd.to_timedelta(df["time_in_sec"], unit="s")
    df.set_index("time_of_day", inplace=True)
    return df


df_81 = load_and_process_data(
    project_root / "inputs" / "schedules" / "empirical_schedule_81.json"
)
df_83 = load_and_process_data(
    project_root / "inputs" / "schedules" / "empirical_schedule_83.json"
)


# %%
def plot_data(df, version):
    fig = go.Figure()
    time = (
        df.index.total_seconds() / 3600
    )  # Convert time to hours for better x-axis labeling

    for direction in df["direction"].unique():
        df_direction = df[df["direction"] == direction]

        df_direction["headway"] = df_direction["headway"] / 60

        # Resample the rolling mean and standard deviation by each minute
        resampled_mean = df_direction["headway"].resample("15T").mean()
        resampled_std = df_direction["headway"].resample("15T").std()

        # Mean line
        fig.add_trace(
            go.Scatter(
                x=resampled_mean.index.total_seconds() / 3600,
                y=resampled_mean,
                mode="lines",
                name=f"{direction} - Rolling Mean Headway",
            )
        )

        # Standard deviation area
        fig.add_trace(
            go.Scatter(
                x=list(resampled_mean.index.total_seconds() / 3600)
                + list(resampled_mean.index.total_seconds() / 3600)[
                    ::-1
                ],  # time values for x-axis
                y=list(resampled_mean + resampled_std)
                + list(resampled_mean - resampled_std)[
                    ::-1
                ],  # upper and lower bounds for y-axis
                fill="toself",
                fillcolor="rgba(0,100,80,0.2)",
                line=dict(color="rgba(255,255,255,0)"),
                name=f"{direction} - Headway ±1 std",
                showlegend=True,
            )
        )

    # Update layout using your template
    fig.update_layout(
        title=f"Rolling Statistics for Version {version}",
        xaxis_title="Time of Day (hours)",
        yaxis_title="Headway (seconds)",
    )

    fig.show(renderer="browser")


plot_data(df_81, 81)
plot_data(df_83, 83)

# %%
