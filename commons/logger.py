import logging

def setup_logger():
    logger = logging.getLogger("API_AUTO_TEST")
    logger.setLevel(logging.INFO)
    logger.handlers.clear()

    # 日志格式
    formatter = logging.Formatter(
        "%(asctime)s - %(levelname)s - %(message)s"
    )

    # 1. 控制台输出
    console_handler = logging.StreamHandler()
    console_handler.setFormatter(formatter)

    # 2. 文件落日志（项目根目录）
    file_handler = logging.FileHandler(
        "api_test_log.txt",
        encoding="utf-8",
        mode="a"   # 追加，不覆盖
    )
    file_handler.setFormatter(formatter)

    logger.addHandler(console_handler)
    logger.addHandler(file_handler)
    return logger

# 全局唯一日志对象，其他文件直接导入用
logger = setup_logger()