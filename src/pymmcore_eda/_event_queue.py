import threading
from collections import defaultdict

from sortedcontainers import SortedSet
from useq import Channel

from pymmcore_eda._eda_event import EDAEvent
from pymmcore_eda._eda_sequence import EDASequence
from pymmcore_eda._logger import logger


class DynamicEventQueue:
    """An event queue for Dynamic acquisitions.

    it tracks unique dimension values and allows indexing by ordinal position.
    """

    def __init__(self) -> None:
        self._events = SortedSet()

        self._unique_indexes: dict[str, SortedSet[int]] = {
            "t": SortedSet(),
            "z": SortedSet(),
            "p": SortedSet(),
            "g": SortedSet(),
        }
        # Channels are special, as they are not integers
        self._channels: tuple[str, ...] = ()

        self._events_by_time: dict[float, list[EDAEvent]] = defaultdict(list)
        self._t_index = 0  # Sequential index counter
        self.sequence = None
        self._lock = threading.Lock()

    def add(self, event: EDAEvent) -> None:
        """Add an event to the queue, resolving any dimension indices in the event."""
        with self._lock:
            if event.sequence and not self.sequence:
                self._apply_sequence(event.sequence)
            if event.attach_index:
                self._apply_dimension_indices(event)
            # Offset time relative
            if event.start_time_offset:
                event.min_start_time += event.start_time_offset

            self._events.add(event)

            if event not in self._events_by_time[event.min_start_time]:
                self._events_by_time[event.min_start_time].append(event)
                self._update_unique_sets(event)
            else:
                logger.info(f"Event rejected, already in queue {event}")
                logger.info(self._events_by_time[event.min_start_time])

    def remove(self, event: EDAEvent) -> None:
        """Remove an event from the queue."""
        with self._lock:
            if event in self._events:
                self._events.remove(event)
            if event.min_start_time is not None:
                self._events_by_time[event.min_start_time].remove(event)
                if len(self._events_by_time[event.min_start_time]) == 0:
                    del self._events_by_time[event.min_start_time]
                    self._unique_indexes["t"].remove(event.min_start_time)
                    self._t_index += 1
            else:
                self._t_index += 1

    def clear(self) -> None:
        """Clear the event queue."""
        with self._lock:
            self._events.clear()
            self._events_by_time.clear()

    def _apply_sequence(self, sequence: EDASequence) -> None:
        """Apply the sequence to the event queue."""
        self.sequence = sequence
        # Initialize unique indexes based on the sequence
        if hasattr(sequence, "channels"):
            self._channels = tuple(c.config for c in sequence.channels)
        if hasattr(sequence, "z_positions"):
            self._unique_indexes["z"] = SortedSet(sequence.z_positions)
        if hasattr(sequence, "positions"):
            self._unique_indexes["p"] = SortedSet(sequence.positions)
        if hasattr(sequence, "grid_positions"):
            self._unique_indexes["g"] = SortedSet(sequence.grid_positions)

    def _apply_dimension_indices(self, event: EDAEvent) -> EDAEvent:
        """Apply dimensional indices from event.attach_index to set actual values."""
        if not event.attach_index:
            return event

        for dim, index in event.attach_index.items():
            value = self.get_value_at_index(dim, index)
            if value is not None:
                if dim == "t":
                    event.min_start_time = value
                elif dim == "c":
                    event.channel = Channel(config=value)
                elif dim == "z":
                    event.z_pos = value
                elif dim == "p":
                    event.pos_index = value
                elif dim == "g":
                    event.pos_name = value
        return event

    def _update_unique_sets(self, event: EDAEvent) -> None:
        """Update the unique value sets with values from this event."""
        if event.min_start_time is not None:
            self._unique_indexes["t"].add(event.min_start_time)
        if event.channel and event.channel.config not in self._channels:
            self._channels = (*self._channels, event.channel.config)
        if event.z_pos is not None:
            self._unique_indexes["z"].add(event.z_pos)
        if event.pos_index is not None:
            self._unique_indexes["p"].add(event.pos_index)
        if event.pos_name is not None:
            self._unique_indexes["g"].add(event.pos_name)

    def get_next(self) -> EDAEvent | None:
        """Get the next event from the queue (first in order)."""
        if len(self._events) == 0:
            return None
        event = self._events.pop(0)
        # Generate and assign integer indexes before returning the event
        event = self._assign_integer_indexes(event)
        self.remove(event)
        return event

    def peak_next(self) -> EDAEvent | None:
        """Peek at the next event in the queue without removing it."""
        if len(self._events) == 0:
            return None

        event = self._events[0]
        # Generate and assign integer indexes before returning a copy of the event
        event_copy = event.model_copy()
        event_copy = self._assign_integer_indexes(event_copy)
        return event_copy

    def _assign_integer_indexes(self, event: EDAEvent) -> EDAEvent:
        """Assign integer indexes to the event based on its dimension values."""
        index = {}

        # Assign channel index if available
        if event.channel is not None and hasattr(event.channel, "config"):
            channel_value = event.channel.config
            channel_index = self._get_index_of_value("c", channel_value)
            if channel_index is not None:
                index["c"] = channel_index

        # Assign z-position index if available
        if event.z_pos is not None:
            z_index = self._get_index_of_value("z", event.z_pos)
            if z_index is not None:
                index["z"] = z_index

        # Assign position index if available
        if event.pos_index is not None:
            pos_index = self._get_index_of_value("p", event.pos_index)
            if pos_index is not None:
                index["p"] = pos_index

        # Assign position name (grid) index if available
        if event.pos_name is not None:
            grid_index = self._get_index_of_value("g", event.pos_name)
            if grid_index is not None:
                index["g"] = grid_index

        # Assign time index if available
        time_index = self._t_index
        index["t"] = time_index

        # Attach the index to the event
        event.index = index
        return event

    def _get_index_of_value(self, dim: str, value: float | str | Channel) -> int | None:
        """Get the integer index of a value in a dimension's unique set."""
        if dim in self._unique_indexes and value in self._unique_indexes[dim]:
            values_list = self._unique_indexes[dim]
            return int(values_list.index(value))
        elif dim == "c" and value in self._channels:
            return self._channels.index(value)
        return None

    def get_value_at_index(self, dim: str, index: int) -> int | str | None | float:
        """Get the value at a specific index for a dimension."""
        if dim in self._unique_indexes.keys():
            values = self._unique_indexes[dim]
            if index < len(values):
                return list(values)[index]  # type: ignore
        elif dim == "c":
            return self._channels[index] if 0 <= index < len(self._channels) else None
        return None

    def get_unique_values(self, dim: str) -> list[int] | tuple:
        """Get all unique values for a dimension."""
        if dim == "c":
            return self._channels
        elif dim in ("t", "z", "p", "g"):
            return list(self._unique_indexes[dim])
        else:
            return []

    def get_events_at_time(self, timestamp: float) -> list[EDAEvent]:
        """Get all events scheduled at a specific timestamp."""
        return self._events_by_time.get(timestamp, [])

    def __len__(self) -> int:
        """Get the number of events in the queue."""
        return len(tuple(self._events))
