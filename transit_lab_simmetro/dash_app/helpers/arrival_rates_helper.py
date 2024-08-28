import pandas as pd
import plotly.graph_objects as go


class ArrivalRatePlotCreator:
    def __init__(self, file_path, stations_dict: dict):
        self.data = pd.read_csv(file_path)
        self.stations_dict = stations_dict

    def get_figure(self, start_hour, end_hour, is_weekday):
        hour_df = self.data[
            (self.data["weekday"] == is_weekday)
            & (self.data["hour"] >= start_hour)
            & (self.data["hour"] < end_hour)
        ]
        pivot_df = hour_df.pivot_table(
            index="origin_stop",
            columns="destination_stop",
            values="arrival_rate",
            aggfunc="mean",
        )

        # Ensure all stations are in the DataFrame
        stations = list(self.stations_dict.keys())
        pivot_df = pivot_df.reindex(index=stations, columns=stations)

        heatmap = go.Heatmap(
            z=pivot_df.values,
            x=pivot_df.columns,
            y=pivot_df.index,
            colorscale="Blues",
            hovertemplate=(
                "<b>Origin</b>: %{y}<br>"
                + "<b>Destination</b>: %{x}<br>"
                + "<b>Pax Arrival Rate</b>: %{z}<extra></extra>"
            ),
        )

        fig = go.Figure(data=heatmap)

        fig.update_layout(
            title=f"Hour: {start_hour} - {end_hour}, Weekday: {is_weekday}",
            xaxis_title="Destination",
            yaxis_title="Origin",
            xaxis_nticks=36,
        )

        return fig
