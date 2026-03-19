from functools import wraps
from .. import BotBook

bb = BotBook()

def agent(name, capabilities):

    def wrapper(fn):

        profile = bb.register_agent(
            name=name,
            capabilities=capabilities
        )

        @wraps(fn)
        def run(*args, **kwargs):
            return fn(*args, **kwargs)

        run.profile = profile
        return run

    return wrapper
