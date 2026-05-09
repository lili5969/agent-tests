
TOOL_REGISTRY = {}

def tool(func):
    """装饰器：自动注册函数到工具表"""
    TOOL_REGISTRY[func.__name__] = func
    return func


TOOL_DEPS = [
    {
        "from_tool": "get_order",
        "to_tool": "get_logistics",
        "input_key": "tracking_id",
        "output_key": "tracking_id"
    },
    {
        "from_tool": "get_logistics",
        "to_tool": "get_delivery_status",
        "input_key": "location",
        "output_key": "location"
    }
]