from typing import TYPE_CHECKING, Any, Self, Union

from pydantic import Field, field_validator
from useq import Channel, MDAEvent, MDASequence, PropertyTuple, SLMImage
from useq._actions import AcquireImage, AnyAction
from useq._base_model import MutableModel

from pymmcore_eda._eda_sequence import EDASequence

try:
    from pydantic import field_serializer
except ImportError:
    field_serializer = None  # type: ignore

if TYPE_CHECKING:
    from collections.abc import Sequence
    from useq import MDAEvent
    ReprArgs = Sequence[tuple[str | None, Any]]


def _float_or_none(v: Any) -> float | None:
    return float(v) if v is not None else v


class EDAEvent(MutableModel):
    """Define a single event in a [`EDASequence`][EDASequence].

    A subset of properties of a useq.MDAEvent that are present before the scheduling.
    """

    index: dict[str, int] | None = None
    attach_index: dict[str, int] | None = None
    channel: Channel | None = None
    exposure: float | None = Field(default=None, gt=0.0)
    min_start_time: float | None = None  # time in sec
    pos_name: str | None = None
    x_pos: float | None = None
    y_pos: float | None = None
    z_pos: float | None = None
    pos_index: int | None = None  # Position index for ordering
    slm_image: SLMImage | None = None
    sequence: Union["EDASequence", "MDASequence"] | None = Field(
        default=None, repr=False
    )
    properties: list[PropertyTuple] | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)
    action: AnyAction = Field(default_factory=AcquireImage, discriminator="type")
    keep_shutter_open: bool = False
    reset_event_timer: bool = False

    @field_validator("channel", mode="before")
    def _validate_channel(cls, val: Any) -> Any:
        return Channel(config=val) if isinstance(val, str) else val

    if field_serializer is not None:
        # Remove problematic field serializers
        _sx = field_serializer("x_pos", mode="plain")(_float_or_none)
        _sy = field_serializer("y_pos", mode="plain")(_float_or_none)
        _sz = field_serializer("z_pos", mode="plain")(_float_or_none)

    def _get_dimension_value(self, dim: str) -> float | str | int | None:
        """Get the value for a specific dimension.

        Parameters
        ----------
        dim : str
            One character from the axis_order tuple ('t', 'p', 'g', 'c', 'z')

        Returns
        -------
        Union[float, str, int, None]
            The value for the dimension, or None if not applicable
        """
        if dim == "t":
            return self.min_start_time
        elif dim == "c":
            # If we have a channel and a sequence, return the channel index in
            # the sequence
            index = self._get_channel_index()
            if index is not False:
                return index
            # Default to channel config for sorting if no sequence is available
            return self.channel.config if self.channel else None
        elif dim == "z":
            return self.z_pos
        elif dim == "p":  # Position index
            return self.pos_index
        elif dim == "g":  # Position group/name
            return self.pos_name
        else:
            return None

    def _get_channel_index(self) -> int | bool:
        if self.channel and self.sequence and hasattr(self.sequence, "channels"):
            # Find the index of this channel in the sequence channels
            channel_config = self.channel.config
            for i, ch in enumerate(self.sequence.channels):
                if isinstance(ch, Channel):
                    if ch.config == channel_config:
                        return i
                elif ch == channel_config:
                    return i
        return False

    def _get_axis_order(self) -> tuple[str, ...]:
        """Get the axis order to use for comparisons."""
        if self.sequence and hasattr(self.sequence, "axis_order"):
            return self.sequence.axis_order
        return ("t", "p", "g", "c", "z")  # Default axis order

    def __lt__(self, other: Self) -> bool:
        """Compare two EDAEvents based on the axis_order from the sequence."""
        if not isinstance(other, EDAEvent):
            return NotImplemented

        # Get axis order from sequence or use the default ('t', 'p', 'g', 'c', 'z')
        axis_order = self._get_axis_order()

        # Compare based on each dimension in the axis order
        for dim in axis_order:
            self_val = self._get_dimension_value(dim)
            other_val = other._get_dimension_value(dim)

            # Skip dimensions where both values are None
            if self_val is None and other_val is None:
                continue

            # None is considered less than any value
            if self_val is None:
                return True
            if other_val is None:
                return False

            # If values differ, return the comparison result
            if self_val != other_val:
                if dim == "z" and hasattr(self.sequence, "z_direction"):
                    # For z-direction comparison, use the sequence's z_direction
                    return self._get_z_comparison(other, self_val, other_val) or False
                # For string comparison (like position group names)
                if (
                    isinstance(self_val, str)
                    and isinstance(other_val, str)
                    and dim != "c"
                ):
                    return self_val < other_val
                # For numeric comparisons (time, position index, z, channel index)
                try:
                    print(dim, self, other, self_val, other_val)
                    return float(self_val) < float(other_val)
                except ValueError:
                    # One of the items could not be indexed, it will go later
                    if isinstance(self_val, str):
                        return False
                    elif isinstance(other_val, str):
                        return True
                    else:
                        print("Error in channel comparison")

        # If everything is equal, this should not matter, the set will reject the event
        return id(self) < id(other)

    def _get_z_comparison(self, other: Self, self_z: Any, other_z: Any) -> bool | None:
        """Determine the z comparison direction based on z_direction property."""
        if not hasattr(self.sequence, "z_direction"):
            return bool(self_z < other_z)  # Default to ascending order

        if self.sequence and isinstance(self.sequence, EDASequence):
            z_direction = self.sequence.z_direction
        else:
            z_direction = "up"  # Default to ascending if no sequence is available

        if z_direction == "up":
            return bool(self_z < other_z)
        elif z_direction == "down":
            return bool(self_z > other_z)
        elif z_direction == "alternate":
            # For alternate mode, even channels go up, odd channels go down
            channel_index = self._get_channel_index()
            if channel_index is False:
                return bool(self_z < other_z)  # Default if channel index not found
            return (
                bool(self_z < other_z)
                if channel_index % 2 == 0
                else bool(self_z > other_z)
            )
        else:
            return bool(self_z < other_z)  # Unknown direction, default to ascending

    def __eq__(self, other: object) -> bool:
        """
        Check if two EDAEvents are equal based on the axis_order from the sequence.

        The axis_order is retrieved from the sequence, or defaults to
        ('t', 'p', 'g', 'c', 'z') if not available.
        """
        if not isinstance(other, EDAEvent):
            return NotImplemented

        # Get axis order from sequence or use the default ('t', 'p', 'g', 'c', 'z')
        axis_order = self._get_axis_order()

        # Compare based on each dimension in the axis order
        for dim in axis_order:
            self_val = self._get_dimension_value(dim)
            other_val = other._get_dimension_value(dim)

            # If values differ, events are not equal
            if self_val != other_val:
                return False

        # All dimensions are equal, additional attributes check
        return (
            self.exposure == other.exposure
            and self.properties == other.properties
            and self.action == other.action
            and self.keep_shutter_open == other.keep_shutter_open
            and self.reset_event_timer == other.reset_event_timer
        )

    def __hash__(self) -> int:
        # Create a hashable representation of the event as in __eq__
        hashable_parts: list[
            PropertyTuple | float | str | int | None | tuple[PropertyTuple, ...]
        ] = []
        axis_order = self._get_axis_order()
        for dim in axis_order:
            val = self._get_dimension_value(dim)
            hashable_parts.append(val)

        hashable_parts.extend(
            [
                self.min_start_time,
                self.exposure,
                # Convert list to tuple since lists aren't hashable
                tuple(self.properties) if self.properties else None,
                # You might need a custom hash for action depending on its type
                hash(self.action)
                if hasattr(self.action, "__hash__")
                else id(self.action),
                self.keep_shutter_open,
                self.reset_event_timer,
            ]
        )

        return hash(tuple(hashable_parts))

    def get_priority_key(
        self, axis_order: tuple[str, ...] | str | None = None
    ) -> tuple[str | float | int, ...]:
        """Create a tuple of values for sorting based on axis order."""
        if axis_order is None:
            axis_order = self._get_axis_order()
        elif isinstance(axis_order, str):
            # Convert string axis_order to tuple for compatibility
            axis_order = tuple(axis_order)

        result: list[str | float | int] = []
        for dim in axis_order:
            val = self._get_dimension_value(dim)
            # Handle None values for stable sorting
            if val is None:
                # Use sentinel values based on dimension type
                if dim in (
                    "g",
                ):  # String dimensions (excluding channel which is now an index)
                    result.append("")  # Empty string for string comparison
                else:  # Numeric dimensions (t, p, z, c)
                    result.append(
                        float("-inf")
                    )  # Negative infinity for numeric comparison
            else:
                result.append(val)
        return tuple(result)

    def from_mda_event(
        self, mda_event: MDAEvent, eda_sequence: EDASequence | None = None
    ) -> Self:
        """Create an EDAEvent from a useq.MDAEvent instance."""
        # Copy all attributes from the MDAEvent
        for key, value in mda_event.model_dump().items():
            if key == "index":
                continue
            if key == "sequence" and value and eda_sequence:
                setattr(self, key, eda_sequence)
                continue
            if key == "sequence" and value:
                setattr(self, key, MDASequence(**value))
                continue

            setattr(self, key, value)
        return self
