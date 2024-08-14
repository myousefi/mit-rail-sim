from typing import List, Optional, TypeVar

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import plotly.io as pio
from plotly.subplots import make_subplots
from typing_extensions import Protocol

from mit_rail_sim.simulation_engine.infrastructure import Path

pio.templates["sophisticated"] = go.layout.Template(
    layout=go.Layout(colorway=["#91393D", "#DEDC83", "#DE6D72", "#57ADDE", "#407491"])
)
pio.templates.default = "sophisticated"


class HasPath(Protocol):
    path: Path  # Indicate that classes implementing this protocol should have a 'path' attribute


class VisualizationMixinBase:
    # Get the colorway from the 'sophisticated' template
    color_palette = pio.templates["sophisticated"].layout.colorway

    def get_color(self, index):
        """Get a color from the color palette based on the index."""
        return self.color_palette[index % len(self.color_palette)]


class HasPathAndVisualizationMixin(HasPath, Protocol):
    def get_color(self, index):
        pass


T = TypeVar("T", bound=HasPathAndVisualizationMixin)


class VisualizationMixin(VisualizationMixinBase):
    def visualize_distance_profiles(
        self: T,
        distances,
        quantity_to_profile,
        title="",
        train_speed_regulator_states: Optional[List] = None,
        current_speed_codes=None,
    ):
        fig = make_subplots()
        colors = px.colors.qualitative.Plotly

        if train_speed_regulator_states is not None:
            data = pd.DataFrame(
                {
                    "distances": distances,
                    "quantity_to_profile": quantity_to_profile,
                    "train_speed_regulator_states": train_speed_regulator_states,
                }
            )

            # Create a list of unique states
            unique_states = data["train_speed_regulator_states"].unique()

            for state, group in data.groupby("train_speed_regulator_states"):
                state_index = unique_states.tolist().index(state)

                fig.add_trace(
                    go.Scatter(
                        x=group["distances"],
                        y=group["quantity_to_profile"],
                        mode="markers",
                        name=state,
                        # marker=dict(color=colors[hash(state) % len(colors)]),
                        marker=dict(color=self.get_color(state_index)),
                        legendgroup=state,
                    ),
                )
        else:
            fig.add_trace(
                go.Scatter(
                    x=distances, y=quantity_to_profile, mode="lines", name=title
                ),
            )

        if current_speed_codes is not None:
            fig.add_trace(
                go.Scatter(
                    x=distances,
                    y=current_speed_codes,
                    mode="lines",
                    name="Current Speed Codes",
                ),
            )

        total_dist: float = 0
        for block in self.path.blocks:
            fig.add_shape(
                type="line",
                x0=block.length + total_dist,
                x1=block.length + total_dist,
                y0=0,
                y1=max(quantity_to_profile),
                yref="y1",
                line=dict(color="#BC544B", dash="dash"),
            )

            if block.station is not None:
                fig.add_shape(
                    type="line",
                    x0=total_dist + block.station.location_relative_to_block,
                    x1=total_dist + block.station.location_relative_to_block,
                    y0=0,
                    y1=max(quantity_to_profile),
                    yref="y1",
                    line=dict(color="#26619c", dash="dash"),
                )
                fig.add_annotation(
                    x=block.station.location_relative_to_block + total_dist,
                    y=max(quantity_to_profile),
                    text=block.station.name,
                    showarrow=True,
                    arrowhead=2,
                    arrowsize=1,
                    arrowwidth=2,
                    arrowcolor="#636363",
                    ax=20,
                    ay=-30,
                    bgcolor="rgba(255, 255, 255, 0.7)",
                    bordercolor="#c7c7c7",
                    borderwidth=2,
                    borderpad=4,
                )

            total_dist = total_dist + block.length

        fig.update_layout(title=title, xaxis_title="Distance", yaxis_title=title)
        fig.show()

    def visualize_time_profile(
        self,
        times,
        profile,
        title="",
        train_speed_regulator_states: Optional[List] = None,
        train_received_speed_codes=None,
    ):
        fig = go.Figure()
        colors = px.colors.qualitative.Plotly

        if train_speed_regulator_states is not None:
            data = pd.DataFrame(
                {
                    "times": times,
                    "profile": profile,
                    "train_speed_regulator_states": train_speed_regulator_states,
                }
            )

            # Create a list of unique states
            unique_states = data["train_speed_regulator_states"].unique()

            for state, group in data.groupby("train_speed_regulator_states"):
                state_index = unique_states.tolist().index(state)

                fig.add_trace(
                    go.Scatter(
                        x=group["times"],
                        y=group["profile"],
                        mode="markers",
                        name=state,
                        marker=dict(color=self.get_color(state_index)),
                        legendgroup=state,
                    ),
                )
        else:
            fig.add_trace(go.Scatter(x=times, y=profile, mode="lines", name=title))

        if train_received_speed_codes is not None:
            fig.add_trace(
                go.Scatter(
                    x=times,
                    y=train_received_speed_codes,
                    mode="lines",
                    name="Current Speed Codes",
                ),
            )

        fig.update_layout(title=title, xaxis_title="Time", yaxis_title=title)
        fig.show()
