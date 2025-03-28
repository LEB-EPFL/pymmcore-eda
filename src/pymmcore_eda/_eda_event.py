from typing import (
    TYPE_CHECKING,
    Any,
    Optional,
    Union,
    Self,
    Tuple,
    Dict,
)

from pydantic import Field, field_validator


from useq._actions import AcquireImage, AnyAction
from useq._base_model import UseqModel
from useq import Channel, PropertyTuple, SLMImage
from useq._mda_sequence import MDASequence

try:
    from pydantic import field_serializer
except ImportError:
    field_serializer = None  # type: ignore

if TYPE_CHECKING:
    from collections.abc import Sequence

    ReprArgs = Sequence[tuple[Optional[str], Any]]

def _float_or_none(v: Any) -> Optional[float]:
    return float(v) if v is not None else v

class EDAEvent(UseqModel):
    """Define a single event in a [`EDASequence`][EDASequence]. A subset of properties of a 
    useq.MDAEvent that are present before the scheduling.
    """

    offset_index: Optional[Dict[str, int]] = None
    channel: Optional[Channel] = None
    exposure: Optional[float] = Field(default=None, gt=0.0)
    min_start_time: Optional[float] = None  # time in sec
    pos_name: Optional[str] = None
    x_pos: Optional[float] = None
    y_pos: Optional[float] = None
    z_pos: Optional[float] = None
    pos_index: Optional[int] = None  # Position index for ordering
    slm_image: Optional[SLMImage] = None
    sequence: Optional["MDASequence"] = Field(default=None, repr=False)
    properties: Optional[list[PropertyTuple]] = None
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

    def _get_dimension_value(self, dim: str) -> Union[float, str, int, None]:
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
        if dim == 't':
            return self.min_start_time
        elif dim == 'c':
            # If we have a channel and a sequence, return the channel index in the sequence
            if self.channel and self.sequence and hasattr(self.sequence, 'channels'):
                # Find the index of this channel in the sequence channels
                channel_config = self.channel.config
                for i, ch in enumerate(self.sequence.channels):
                    if ch.config == channel_config:
                        return i
            # Default to channel config for sorting if no sequence is available
            return self.channel.config if self.channel else None
        elif dim == 'z':
            return self.z_pos
        elif dim == 'p':  # Position index
            return self.pos_index
        elif dim == 'g':  # Position group/name
            return self.pos_name
        else:
            return None
    
    def _get_axis_order(self) -> tuple[str, ...]:
        """Get the axis order to use for comparisons.
        
        Returns
        -------
        tuple[str, ...]
            The axis order tuple, defaulting to ('t', 'p', 'g', 'c', 'z') if not available from sequence
        """
        if self.sequence and hasattr(self.sequence, 'axis_order'):
            return self.sequence.axis_order
        return ('t', 'p', 'g', 'c', 'z')  # Default axis order
    
    def __lt__(self, other: Self) -> bool:
        """
        Compare two EDAEvents based on the axis_order from the sequence.
        
        The axis_order is retrieved from the sequence, or defaults to ('t', 'p', 'g', 'c', 'z') if not available.
        """
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
                # For string comparison (like position group names)
                if isinstance(self_val, str) and isinstance(other_val, str) and dim != 'c':
                    return self_val < other_val
                # For numeric comparisons (time, position index, z, channel index)
                return float(self_val) < float(other_val)
                
        # If all dimensions are equal, events are considered equal for ordering
        # In this case, we'll use the object id as a tiebreaker for consistent ordering
        return id(self) < id(other)
    
    def __eq__(self, other: object) -> bool:
        """
        Check if two EDAEvents are equal based on the axis_order from the sequence.
        
        The axis_order is retrieved from the sequence, or defaults to ('t', 'p', 'g', 'c', 'z') if not available.
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
            self.exposure == other.exposure and
            self.properties == other.properties and
            self.action == other.action and
            self.keep_shutter_open == other.keep_shutter_open and
            self.reset_event_timer == other.reset_event_timer
        )
    
    def get_priority_key(self, axis_order: Union[tuple[str, ...], str] = None) -> Tuple:
        """
        Create a tuple of values for sorting based on axis order.
        This can be used with sorted() function.
        
        Parameters
        ----------
        axis_order : tuple[str, ...] or str, optional
            The axis order to use. If None, uses the one from the sequence
            or defaults to ('t', 'p', 'g', 'c', 'z').
            
        Returns
        -------
        Tuple
            A tuple of values suitable for sorting
            
        Example
        -------
        sorted_events = sorted(events, key=lambda event: event.get_priority_key(('t','p','g','c','z')))
        """
        if axis_order is None:
            axis_order = self._get_axis_order()
        elif isinstance(axis_order, str):
            # Convert string axis_order to tuple for compatibility
            axis_order = tuple(axis_order)
            
        result = []
        for dim in axis_order:
            val = self._get_dimension_value(dim)
            # Handle None values for stable sorting
            if val is None:
                # Use sentinel values based on dimension type
                if dim in ('g',):  # String dimensions (excluding channel which is now an index)
                    result.append("")  # Empty string for string comparison
                else:  # Numeric dimensions (t, p, z, c)
                    result.append(float('-inf'))  # Negative infinity for numeric comparison
            else:
                result.append(val)
        return tuple(result)