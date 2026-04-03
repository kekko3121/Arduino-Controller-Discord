import asyncio
import logging

logger = logging.getLogger(__name__) # Logger for this module

# This class manages the current mute and deafen states in a thread-safe manner
class AudioState:
    def __init__(self):
        self.mute_state = False # Indicates value of the mute state. False = unmuted, True = muted
        self.deafen_state = False # Indicates value of the deafen state. False = undeafened, True = deafened
        self._lock = asyncio.Lock() # Lock to ensure thread-safe access to states

    # Thread-safe update and retrieval of states
    async def update(self, muted=None, deafened=None):
        async with self._lock: # Acquire lock to safely update states
            if muted is not None: self.mute_state = muted # Update mute state if provided
            if deafened is not None: self.deafen_state = deafened # Update deafen state if provided
            return {'muted': self.mute_state, 'deafened': self.deafen_state} # Return current states after update

    # Thread-safe retrieval of current states without modification
    async def get_states(self):
        async with self._lock: # Acquire lock to safely read states
            return {'muted': self.mute_state, 'deafened': self.deafen_state} # Return current states