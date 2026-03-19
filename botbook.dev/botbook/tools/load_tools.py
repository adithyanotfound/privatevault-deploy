from botbook.tools.registry import register_tool
from botbook.tools.external_tools import http_get, weather, exchange_rate

register_tool("http_get", http_get)
register_tool("weather", weather)
register_tool("exchange_rate", exchange_rate)
