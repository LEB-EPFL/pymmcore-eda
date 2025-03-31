from typing import (
    List,
    Optional,
    Tuple,
    Dict,
    Any,
    Union,
    Set
)

from pydantic import Field, field_validator

from useq._base_model import MutableModel
from useq import Channel


class EDASequence(MutableModel):
    """
    Defines a sequence for Event-Driven Acquisition (EDA).
    
    The EDASequence contains configuration for the acquisition process,
    including axis order, channels, and components for analysis and actuation.
    Events are managed outside this class.
    """
    
    # Main components
    analyzer: Optional[Any] = None  # Component that analyzes images
    interpreter: Optional[Any] = None  # Component that interprets analysis results
    actuator: Optional[Any] = None  # Component that executes actions based on interpretation
    
    # Configuration
    axis_order: Union[str, Tuple[str, ...]] = Field(default=('t', 'p', 'g', 'c', 'z'))
    channels: Union[Tuple[str, ...], Tuple[Channel, ...]] = Field(default_factory=list)
    channel_group: Optional[str] = None
    
    @field_validator("axis_order", mode="before")
    def _validate_axis_order(cls, val: Any) -> Tuple[str, ...]:
        """Convert string axis_order to tuple format."""
        if isinstance(val, str):
            return tuple(val)
        return val

    @field_validator("channels", mode="before")
    def _validate_channels(cls, val: Any) -> Tuple[Channel, ...]:
        """Convert string axis_order to tuple format."""
        if len(val) == 0:
            return tuple()
        if isinstance(val[0], str):
            return tuple(Channel(config=c) for c in val)
        return val
    
    # Properties
    properties: Dict[str, Any] = Field(default_factory=dict)
    metadata: Dict[str, Any] = Field(default_factory=dict)
    
    def get_channel_index(self, channel_config: str) -> Optional[int]:
        """
        Get the index of a channel in the sequence.
        
        Parameters
        ----------
        channel_config : str
            The channel configuration to look for.
            
        Returns
        -------
        Optional[int]
            The index of the channel, or None if not found.
        """
        try:
            return self.channels.index(channel_config)
        except ValueError:
            return None
    
    def set_analyzer(self, analyzer: Any) -> 'EDASequence':
        """Set the analyzer component and return self for chaining."""
        self.analyzer = analyzer
        return self
    
    def set_interpreter(self, interpreter: Any) -> 'EDASequence':
        """Set the interpreter component and return self for chaining."""
        self.interpreter = interpreter
        return self
    
    def set_actuator(self, actuator: Any) -> 'EDASequence':
        """Set the actuator component and return self for chaining."""
        self.actuator = actuator
        return self
    
    def set_axis_order(self, axis_order: Union[str, Tuple[str, ...]]) -> 'EDASequence':
        """
        Set the axis order and return self for chaining.
        
        Parameters
        ----------
        axis_order : Union[str, Tuple[str, ...]]
            The axis order to use, either as a string (e.g., "tpgcz") or
            as a tuple (e.g., ('t', 'p', 'g', 'c', 'z')).
            
        Returns
        -------
        EDASequence
            The sequence instance for chaining.
        """
        self.axis_order = axis_order
        return self
    
    def add_channels(self, channels: List[str], channel_group: Optional[str] = None) -> 'EDASequence':
        """
        Add channels to the sequence.
        
        Parameters
        ----------
        channels : List[str]
            List of channel configurations to add.
        channel_group : Optional[str]
            The channel group, if applicable.
            
        Returns
        -------
        EDASequence
            The sequence instance for chaining.
        """
        self.channels.extend(channels)
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