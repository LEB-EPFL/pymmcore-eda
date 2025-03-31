from queue import PriorityQueue
from sortedcontainers import SortedDict, SortedSet
from collections import defaultdict
from useq import Channel

class DynamicEventQueue:
    """An event queue that tracks unique dimension values and allows indexing by ordinal position."""
    
    def __init__(self):
        self._events = PriorityQueue()
        self._size = 0
        
        self._time_index = SortedDict()
        
        self._unique_indexes = {
            'c': set(),  
            'z': SortedSet(),  
            'p': SortedSet(),  
            'g': SortedSet() 
        }
        
        self._events_by_time = defaultdict(list)
        self._t_index = 0  # Sequential index counter
        self.sequence = None
    
    def add(self, event):
        """Add an event to the queue, resolving any dimension indices in the event."""
        if event.sequence and  not self.sequence:
            self._apply_sequence(event.sequence)
        if event.attach_index:
            self._apply_dimension_indices(event)
        
        self._events.put(event)
        self._size += 1
        self._update_unique_sets(event)
        
        if event.min_start_time is not None:
            self._events_by_time[event.min_start_time].append(event)
    
    def _apply_sequence(self, sequence):
        """Apply the sequence to the event queue."""
        self.sequence = sequence
        
        # Initialize unique indexes based on the sequence
        if hasattr(sequence, 'channels'):
            print('sequence channels', sequence.channels)
            self._unique_indexes['c'] = set(c.config for c in sequence.channels)
        
        if hasattr(sequence, 'z_positions'):
            self._unique_indexes['z'] = SortedSet(sequence.z_positions)
        
        if hasattr(sequence, 'positions'):
            self._unique_indexes['p'] = SortedSet(sequence.positions)
        
        if hasattr(sequence, 'grid_positions'):
            self._unique_indexes['g'] = SortedSet(sequence.grid_positions)

    def _apply_dimension_indices(self, event):
        """Apply dimensional indices from event.attach_index to set actual values."""
        if not event.attach_index:
            return
            
        for dim, index in event.attach_index.items():
            value = self.get_value_at_index(dim, index)
            if value is not None:
                if dim == 't':
                    event.min_start_time = value
                elif dim == 'c':
                    event.channel = Channel(config=value)
                elif dim == 'z':
                    event.z_pos = value
                elif dim == 'p':
                    event.pos_index = value
                elif dim == 'g':
                    event.pos_name = value
    
    def _update_unique_sets(self, event):
        """Update the unique value sets with values from this event."""
        if event.min_start_time is not None:
            timestamp = event.min_start_time
            if timestamp in self._time_index:
                self._time_index[timestamp] += 1
            else:
                self._time_index[timestamp] = 1
        
        if event.channel is not None:
            print('index', self._unique_indexes)
            self._unique_indexes['c'].add(event.channel.config)
            
        if event.z_pos is not None:
            self._unique_indexes['z'].add(event.z_pos)
            
        if event.pos_index is not None:
            self._unique_indexes['p'].add(event.pos_index)
            
        if event.pos_name is not None:
            self._unique_indexes['g'].add(event.pos_name)
    
    def get_next(self):
        """Get the next event from the queue (first in order)."""
        if self._size == 0:
            return None
        
        self._size -= 1
        event = self._events.get()
        
        # Generate and assign integer indexes before returning the event
        self._assign_integer_indexes(event)
        
        if event.min_start_time is not None:
            timestamp = event.min_start_time
            self._time_index[timestamp] -= 1
            
            if self._time_index[timestamp] <= 0:
                del self._time_index[timestamp]
                self._t_index += 1
                if timestamp in self._events_by_time:
                    del self._events_by_time[timestamp]
        
        return event
    
    def _assign_integer_indexes(self, event):
        """Assign integer indexes to the event based on its dimension values."""
        index = {}
        
        # Assign channel index if available
        if event.channel is not None and hasattr(event.channel, 'config'):
            channel_value = event.channel.config
            channel_index = self._get_index_of_value('c', channel_value)
            if channel_index is not None:
                index['c'] = channel_index
        
        # Assign z-position index if available
        if event.z_pos is not None:
            z_index = self._get_index_of_value('z', event.z_pos)
            if z_index is not None:
                index['z'] = z_index
        
        # Assign position index if available
        if event.pos_index is not None:
            pos_index = self._get_index_of_value('p', event.pos_index)
            if pos_index is not None:
                index['p'] = pos_index
        
        # Assign position name (grid) index if available
        if event.pos_name is not None:
            grid_index = self._get_index_of_value('g', event.pos_name)
            if grid_index is not None:
                index['g'] = grid_index
        
        # Assign time index if available
        if event.min_start_time is not None:
            time_list = list(self._time_index.keys())
            try:
                time_index = time_list.index(event.min_start_time)
                index['t'] = time_index
            except ValueError:
                pass  # Time not found in index
        
        # Assign sequential index
        index['t'] = self._t_index

        
        # Attach the index to the event
        event.index = index
    
    def _get_index_of_value(self, dim, value):
        """Get the integer index of a value in a dimension's unique set."""
        if dim in self._unique_indexes and value in self._unique_indexes[dim]:
            values_list = list(self._unique_indexes[dim])
            return values_list.index(value)
        return None
    
    def get_value_at_index(self, dim, index):
        """Get the value at a specific index for a dimension."""
        if dim == 't':
            if 0 <= index < len(self._time_index):
                return list(self._time_index.keys())[index]
        elif dim in self._unique_indexes:
            if 0 <= index < len(self._unique_indexes[dim]):
                return list(self._unique_indexes[dim])[index]
                
        return None
    
    def get_unique_values(self, dim):
        """Get all unique values for a dimension."""
        if dim == 't':
            return list(self._time_index.keys())
        elif dim in self._unique_indexes:
            return list(self._unique_indexes[dim])
            
        return []
    
    def get_events_at_time(self, timestamp):
        """Get all events scheduled at a specific timestamp."""
        return self._events_by_time.get(timestamp, [])
    
    def get_time_count(self, timestamp):
        """Get the count of events at a specific timestamp."""
        return self._time_index.get(timestamp, 0)
    
    def get_next_time(self):
        if len(self._time_index) == 0:
            return None
        return self._time_index.keys()[0]

    def __len__(self):
        """Return the number of events in the queue."""
        return self._size