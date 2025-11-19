# # backend/app/__init__.py
# """
# 金融趋势分析后端应用包
# 提供实时金融趋势数据API接口
# """
#
# import os
# import sys
# import logging
# from pathlib import Path
#
# # 包元数据
# __version__ = "1.0.0"
# __author__ = "Financial Analytics Team"
# __description__ = "实时金融新闻趋势分析与可视化API"
#
# # 设置包级别的日志器
# logger = logging.getLogger(__name__)
#
#
# def setup_logging(level=logging.INFO):
#     """设置日志配置"""
#     logging.basicConfig(
#         level=level,
#         format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
#         datefmt='%Y-%m-%d %H:%M:%S'
#     )
#
#
# # 包初始化时执行的代码
# def init_package():
#     """包初始化函数"""
#     logger.info(f"初始化 {__name__} 包 v{__version__}")
#
#     # 检查必要的环境配置
#     try:
#         # 使用相对导入
#         from .config import settings
#         logger.info(f"应用配置加载成功: {settings.APP_NAME}")
#
#         # 检查Redis配置
#         logger.info(f"Redis配置: {settings.REDIS_HOST}:{settings.REDIS_PORT}/DB{settings.REDIS_DB}")
#
#     except ImportError as e:
#         logger.warning(f"配置加载警告: {e}")
#         # 尝试绝对导入
#         try:
#             from app.config import settings
#             logger.info(f"通过绝对导入加载配置成功: {settings.APP_NAME}")
#         except ImportError:
#             logger.error("无法加载配置，请检查config.py文件")
#     except Exception as e:
#         logger.warning(f"包初始化过程中出现警告: {e}")
#
#
# # 自动执行初始化
# try:
#     setup_logging(logging.INFO)
#     init_package()
# except Exception as e:
#     print(f"包初始化过程中出现错误: {e}")
#
# # 定义包的公开接口
# __all__ = [
#     "app",
#     "settings",
#     "logger",
#     "setup_logging"
# ]
#
#
# # 延迟导入主要组件，避免循环导入问题
# def get_app():
#     """获取FastAPI应用实例"""
#     try:
#         from .main import app
#         return app
#     except ImportError:
#         try:
#             from app.main import app
#             return app
#         except ImportError as e:
#             logger.error(f"无法导入app: {e}")
#             return None
#
#
# def get_settings():
#     """获取配置实例"""
#     try:
#         from .config import settings
#         return settings
#     except ImportError:
#         try:
#             from app.config import settings
#             return settings
#         except ImportError as e:
#             logger.error(f"无法导入settings: {e}")
#             return None
#
#
# # 为方便使用，可以直接导入主要组件
# try:
#     from .main import app
#     from .config import settings
#
#     logger.info("主要组件导入成功")
# except ImportError as e:
#     logger.warning(f"导入包组件时出现警告: {e}")
#     # 尝试绝对导入
#     try:
#         from app.main import app
#         from app.config import settings
#
#         logger.info("通过绝对导入加载主要组件成功")
#     except ImportError:
#         logger.warning("绝对导入也失败，请在运行时检查")
#         app = None
#         settings = None