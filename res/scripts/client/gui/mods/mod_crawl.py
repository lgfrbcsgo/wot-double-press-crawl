from functools import wraps
import BigWorld
import CommandMapping
from debug_utils import LOG_CURRENT_EXCEPTION
from Avatar import PlayerAvatar, _MOVEMENT_FLAGS, _INIT_STEPS


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


class CreepInputHandler:
    def __init__(self):
        self._last_pressed_key = None
        self._last_pressed_key_time = 0
        self.cruise_speed_modifier = 0

    def handle_key_event(self, avatar, is_down, key):
        if not avatar.userSeesWorld() or not avatar._PlayerAvatar__initProgress & _INIT_STEPS.VEHICLE_ENTERED:
            return

        double_down = False
        time = BigWorld.time()

        if is_down:
            if key == self._last_pressed_key and time - self._last_pressed_key_time < 0.35:
                double_down = True
            self._last_pressed_key = key
            self._last_pressed_key_time = time

        if CommandMapping.g_instance.isFired(CommandMapping.CMD_MOVE_FORWARD, key):
            self.cruise_speed_modifier = _MOVEMENT_FLAGS.CRUISE_CONTROL25 if double_down else 0
        elif CommandMapping.g_instance.isFired(CommandMapping.CMD_MOVE_BACKWARD, key):
            self.cruise_speed_modifier = _MOVEMENT_FLAGS.CRUISE_CONTROL50 if double_down else 0


creep_handler = CreepInputHandler()


@run_after(PlayerAvatar, 'makeVehicleMovementCommandByKeys')
def modify_command(return_val, *args, **kwargs):
    return return_val | creep_handler.cruise_speed_modifier


@run_before(PlayerAvatar, 'handleKey')
def handle_key_event(avatar, is_down, key, *args, **kwargs):
    creep_handler.handle_key_event(avatar, is_down, key)
