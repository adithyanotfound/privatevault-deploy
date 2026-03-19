TOOLS = {}

def register(name, func):
    TOOLS[name] = func

def call(name, arg):

    if name not in TOOLS:
        raise Exception("Tool not found: " + name)

    return TOOLS[name](arg)
