from queue import PriorityQueue
from sortedcontainers import SortedSet

class DynamicEventQueue:
    """An event queue that tracks unique dimension values and allows indexing by ordinal position."""
    
    def __init__(self):
        # Main priority queue of events
        self._events = PriorityQueue()
        self._size = 0
        
        # SortedSets of unique values for each dimension
        self._unique_indexes = {
            't': SortedSet(),  
            'c': SortedSet(),  
            'z': SortedSet(),  
            'p': SortedSet(),  
            'g': SortedSet() 
        }
    
    def add(self, event):
        """Add an event to the queue, resolving any dimension indices in the event."""
        # Apply any dimensional indices from event.attach_index
        if event.attach_index:
            self._apply_dimension_indices(event)
        
        self._events.put(event)
        self._size += 1
        self._update_unique_sets(event)
    
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
                    from useq import Channel
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
            self._unique_indexes['t'].add(event.min_start_time)
        
        if event.channel is not None:
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
        return self._events.get()
    
    def get_value_at_index(self, dim, index):
        """Get the value at a specific index for a dimension."""
        if dim in self._unique_indexes and 0 <= index < len(self._unique_indexes[dim]):
            return list(self._unique_indexes[dim])[index]
        return None
    
    def get_unique_values(self, dim):
        """Get all unique values for a dimension."""
        if dim in self._unique_indexes:
            return list(self._unique_indexes[dim])
        return []
    
    def __len__(self):
        """Return the number of events in the queue."""
        return self._size