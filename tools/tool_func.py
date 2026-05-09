from tool_registry import tool

@tool
def get_weather(city: str) -> str:
    """查询城市天气"""
    weather_data = {
        "上海": "今天晴气温在28°，紫外线较强请注意防晒！",
        "北京": "今天气温在18°，有小雨请记得带伞！"
    }
    if city in weather_data:
        return weather_data[city]
    return f"无法查询{city}的天气，请提供具体城市名（如：上海、北京）"

@tool
def get_time(location: str) -> str:
    """查询时间"""
    return f"{location}现在是早上8点，是大脑最清醒的时候，开始美好的一天吧。"

@tool
def get_order(order_id: str) -> dict:
    """查询订单"""
    return {"tracking_id": "TRK_001", "status": "shipped"}

@tool
def get_logistics(tracking_id: str) -> dict:
    """查询物流"""
    return {"location": "上海"}

@tool
def get_delivery_status(location: str) -> dict:
    """查询配送状态"""
    return {"estimate": "明天到达"}

@tool
def add(a: int, b: int) -> int:
    """加法"""
    return a + b

@tool
def multiply(a: int, b: int) -> int:
    """乘法"""
    return a * b

@tool
def book_ticket(from_city: str, to_city: str, date: str) -> str:
    """订票"""
    return f'从{from_city}到{to_city}机票买好了，时间是{date}'