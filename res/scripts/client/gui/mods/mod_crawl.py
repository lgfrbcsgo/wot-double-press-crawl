import re
import json
from functools import wraps
import Keys
import BigWorld
import CommandMapping
from debug_utils import LOG_CURRENT_EXCEPTION
from Avatar import PlayerAvatar, _MOVEMENT_FLAGS, _INIT_STEPS


def load_json_from_file(file_path):
    try:
        with open(file_path, 'r') as json_file:
            # credits to https://regex101.com/r/fJ1aC6/1
            # not perfect though, "//" in strings will be matched as comments!
            without_comments = re.sub('(\/\*[\S\s]*?\*\/)|(\/\/[^\n]*)', '', json_file.read(), flags=re.M)
            return json.loads(without_comments)
    except (IOError, ValueError):
        return None


def hook(hook_handler):
    def build_decorator(module, func_name):
        def decorator(func):
            orig_func = getattr(module, func_name)

            @wraps(orig_func)
            def func_wrapper(*args, **kwargs):
                return hook_handler(orig_func, func, *args, **kwargs)

            setattr(module, func_name, func_wrapper)
            return func
        return decorator
    return build_decorator


@hook
def run_before(orig_func, func, *args, **kwargs):
    try:
        func(*args, **kwargs)
    except:
        LOG_CURRENT_EXCEPTION()
    finally:
        return orig_func(*args, **kwargs)


@hook
def run_after(orig_func, func, *args, **kwargs):
    return_val = orig_func(*args, **kwargs)
    try:
        return_val = func(return_val, *args, **kwargs)
    except:
        LOG_CURRENT_EXCEPTION()
    finally:
        return return_val


class CrawlInputHandler:
    def __init__(self, config=None):
        config = config if config is not None else {}

        double_press = config.get('double_press', {})
        self.double_press_enabled = double_press.get('enabled', False)
        self.double_press_min_delay = double_press.get('min_delay', 0)
        self.double_press_max_delay = double_press.get('max_delay', 0.35)

        hotkey = config.get('hotkey', {})
        self.hotkey_enabled = hotkey.get('enabled', False)
        self.hotkey_key = getattr(Keys, 'KEY_%s' % hotkey.get('key', ''), Keys.KEY_LCONTROL)

        self._last_pressed_key = None
        self._last_pressed_key_time = 0
        self.cruise_speed_modifier = 0

    def handle_key_event(self, is_down, key):
        activated = False

        if is_down and self.double_press_enabled:
            time = BigWorld.time()
            delay = time - self._last_pressed_key_time
            if key == self._last_pressed_key and self.double_press_min_delay < delay < self.double_press_max_delay:
                activated = True
            self._last_pressed_key = key
            self._last_pressed_key_time = time

        activated = activated or (self.hotkey_enabled and BigWorld.isKeyDown(self.hotkey_key))

        if CommandMapping.g_instance.isFired(CommandMapping.CMD_MOVE_FORWARD, key):
            self.cruise_speed_modifier = _MOVEMENT_FLAGS.CRUISE_CONTROL25 if activated else 0
        elif CommandMapping.g_instance.isFired(CommandMapping.CMD_MOVE_BACKWARD, key):
            self.cruise_speed_modifier = _MOVEMENT_FLAGS.CRUISE_CONTROL50 if activated else 0


creep_handler = CrawlInputHandler(config=load_json_from_file('mods/configs/crawl.json'))


@run_after(PlayerAvatar, 'makeVehicleMovementCommandByKeys')
def modify_command(return_val, *args, **kwargs):
    return return_val | creep_handler.cruise_speed_modifier


@run_before(PlayerAvatar, 'handleKey')
def handle_key_event(avatar, is_down, key, *args, **kwargs):
    if not avatar.userSeesWorld() or not avatar._PlayerAvatar__initProgress & _INIT_STEPS.VEHICLE_ENTERED:
        return

    creep_handler.handle_key_event(is_down, key)
