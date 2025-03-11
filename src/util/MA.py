import numpy as np

class MovingAverage:
    
    def __init__(self, window_size=100):
        self.window_size = window_size
        self.temp_ranges = np.array([])
        self.current = None

    def update(self, new_value):
        """Add new value and compute moving average."""
        self.temp_ranges = np.append(self.temp_ranges, new_value)
        
        # Keep only the latest 'window_size' elements
        if len(self.temp_ranges) > self.window_size:
            self.temp_ranges = self.temp_ranges[-self.window_size:]

        # Compute moving average
        self.current = np.mean(self.temp_ranges)
        return self.current
    
    def get_current(self):
        return self.current
