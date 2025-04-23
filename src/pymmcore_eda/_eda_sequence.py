from typing import Any

from pydantic import Field, field_validator
from useq import Channel, MDASequence
from useq._base_model import MutableModel


class EDASequence(MutableModel):
    """
    Defines a sequence for Event-Driven Acquisition (EDA).

    The EDASequence contains configuration for the acquisition process,
    including axis order, channels, and components for analysis and actuation.
    Events are managed outside this class.
    """

    # Main components
    analyzer: Any | None = None  # Component that analyzes images
    interpreter: Any | None = None  # Component that interprets analysis results
    actuator: Any | None = (
        None  # Component that executes actions based on interpretation
    )

    # Configuration
    axis_order: str | tuple[str, ...] = Field(default=("t", "p", "g", "c", "z"))
    channels: tuple[Channel, ...] = Field(default_factory=tuple)
    channel_group: str | None = None
    z_direction: str = (
        "up"  # Direction of Z movement, either "up", "down" or "alternate"
    )

    @field_validator("axis_order", mode="before")
    def _validate_axis_order(cls, val: str | tuple[str, ...]) -> tuple[str, ...]:
        """Convert string axis_order to tuple format."""
        if isinstance(val, str):
            return tuple(val)
        elif isinstance(val, tuple) and val[0]:
            return val
        return ("t", "p", "g", "c", "z")

    @field_validator("channels", mode="before")
    def _validate_channels(
        cls, val: tuple[str, ...] | tuple[Channel, ...]
    ) -> tuple[Channel, ...]:
        """Convert string axis_order to tuple format."""
        if len(val) == 0:
            return ()
        if isinstance(val[0], str):
            return tuple(Channel(config=c) for c in val)
        elif isinstance(val[0], Channel):  # Explicitly check it's a Channel
            return val  # type: ignore
        else:
            raise TypeError(f"Expected tuple of str or Channel, got {type(val[0])}")

    # Properties
    properties: dict[str, Any] = Field(default_factory=dict)
    metadata: dict[str, Any] = Field(default_factory=dict)

    def get_channel_index(self, channel_config: str) -> int | None:
        """Get the index of a channel in the sequence."""
        try:
            return self.channels.index(channel_config)
        except ValueError:
            return None

    def set_analyzer(self, analyzer: Any) -> "EDASequence":
        """Set the analyzer component and return self for chaining."""
        self.analyzer = analyzer
        return self

    def set_interpreter(self, interpreter: Any) -> "EDASequence":
        """Set the interpreter component and return self for chaining."""
        self.interpreter = interpreter
        return self

    def set_actuator(self, actuator: Any) -> "EDASequence":
        """Set the actuator component and return self for chaining."""
        self.actuator = actuator
        return self

    def set_axis_order(self, axis_order: str | tuple[str, ...]) -> "EDASequence":
        """Set the axis order and return self for chaining."""
        self.axis_order = axis_order
        return self

    def add_channels(
        self,
        channels: tuple[str, ...] | tuple[Channel, ...],
        channel_group: str | None = None,
    ) -> "EDASequence":
        """Add channels to the sequence."""
        adding_channels: list[Channel] = []
        for channel in channels:
            if isinstance(channel, str):
                channel = Channel(config=channel)
            adding_channels.append(channel)
        self.channels = self.channels + tuple(adding_channels)
        if channel_group:
            self.channel_group = channel_group
        return self

    def __repr__(self) -> str:
        """Get a string representation of the sequence."""
        components = []
        if self.analyzer:
            components.append("analyzer")
        if self.interpreter:
            components.append("interpreter")
        if self.actuator:
            components.append("actuator")

        return (
            f"EDASequence(components=[{', '.join(components)}], "
            f"channels={len(self.channels)}, "
            f"axis_order={self.axis_order})"
        )

    def from_mda_sequence(self, mda_sequence: MDASequence) -> "EDASequence":
        """Create an EDASequence from a MDASequence."""
        for key, value in mda_sequence.model_dump().items():
            if key == "axis_order":
                self.axis_order = tuple(value)
            if key == "channel_group":
                setattr(self, key, value)
            if key == "channels":
                self.channels = tuple(Channel(**c) for c in value)

        return self
