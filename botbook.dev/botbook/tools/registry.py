TOOLS = {}

def register_tool(name, func):
    TOOLS[name] = func

def get_tool(name):
    return TOOLS.get(name)

def list_tools():
    return list(TOOLS.keys())
