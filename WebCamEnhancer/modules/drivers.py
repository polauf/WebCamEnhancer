from ..core.base import Driver


class Presence(Driver):

    CONFIG_TEMPLATE = {
        "present_filter": "Background",
        "away_filter": "Away"
    }

    def prepare(self):
        self.names = {self.config["present_filter"], self.config["away_filter"]}

    def resolve(self):
        active = self.names - set(self.worker._active_filters)
        if not active:
            return
        active = active[0] 
        # ...



def resolve_away(changer, mask, state=[Config.PRESENT_FILTER, 0, True]):
    # TODO: Optimize conditions. To mutch gunk.
    if state[0] != changer._filter:
        state[0] = changer._filter
    if state[1] > Config.AWAY_FRAMES and state[0] == Config.PRESENT_FILTER:
        state[0] = Config.AWAY_FILTER
        state[1] = 0
        changer._filter = state[0]
    elif state[1] > Config.PRESET_FRAMES and state[0] == Config.AWAY_FILTER:
        state[0] = Config.PRESENT_FILTER
        state[1] = 0
        changer._filter = state[0]
    elif state[0] == Config.PRESENT_FILTER:
        val = np.average(mask) < Config.AWAY_TRESHOLD
        if val and state[2]:
            state[1] += 1
            state[2] = val
        else:
            state[1] = 0
    elif state[0] == Config.AWAY_FILTER:
        val = np.average(mask) > Config.AWAY_TRESHOLD
        if val and state[2]:
            state[1] += 1
            state[2] = val
        else:
            state[1] = 0
    # Prints warning
    frames = Config.AWAY_FRAMES if state[0] == Config.PRESENT_FILTER else Config.PRESET_FRAMES
    if state[1] and state[1] > (frames - changer.fps*Config.WARNING_SECS) and not (state[1]%changer.fps):
        changer.logger.info(f"Changing {state[0]} in {int((frames - state[1])/changer.fps)}.")