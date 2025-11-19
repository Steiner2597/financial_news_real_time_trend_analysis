# backend/app/config.py
import os
from typing import List


class Settings:
    """应用配置类"""

    # 应用基础配置
    APP_NAME: str = "金融趋势分析API"
    VERSION: str = "1.0.0"
    DEBUG: bool = True
    HOST: str = "127.0.0.1"
    PORT: int = 8000

    # Redis配置
    REDIS_HOST: str = "localhost"
    REDIS_PORT: int = 6379
    REDIS_DB: int = 2  # 使用DB2（从 Processor 读取）
    REDIS_PASSWORD: str = None  # 如果没有密码设为None
    REDIS_DECODE_RESPONSES: bool = True

    # Redis键名配置
    REDIS_TREND_DATA_KEY: str = "financial_trend_data"  # 完整趋势数据
    REDIS_TREND_METADATA_FIELD: str = "metadata"  # 元数据字段
    REDIS_TREND_KEYWORDS_FIELD: str = "trending_keywords"  # 热词数据字段

    # CORS配置
    ALLOWED_ORIGINS: List[str] = [
        "http://localhost:3000",
        "http://127.0.0.1:3000",
        "http://localhost:5173",  # Vite默认端口
        "http://127.0.0.1:5173",
    ]

    # API配置
    API_V1_PREFIX: str = "/api/v1"
    UPDATE_INTERVAL: int = 30  # 数据更新间隔(分钟)

    # 安全配置
    # SECRET_KEY: str = "your-secret-key-here"  # 生产环境请修改

    @property
    def redis_url(self) -> str:
        """生成Redis连接URL"""
        if self.REDIS_PASSWORD:
            return f"redis://:{self.REDIS_PASSWORD}@{self.REDIS_HOST}:{self.REDIS_PORT}/{self.REDIS_DB}"
        else:
            return f"redis://{self.REDIS_HOST}:{self.REDIS_PORT}/{self.REDIS_DB}"


# 创建全局配置实例
settings = Settings()
