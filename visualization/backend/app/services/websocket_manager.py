# backend/app/services/websocket_manager.py
from fastapi import WebSocket, WebSocketDisconnect
import json
import asyncio
import logging
from typing import Dict, List, Any, Callable
from datetime import datetime
from enum import Enum

logger = logging.getLogger(__name__)


class DataType(Enum):
    WORD_CLOUD = "word_cloud"
    TRENDING = "trending"
    NEWS = "news"
    ALL = "all"


class ConnectionManager:
    """统一的 WebSocket 连接管理器"""

    def __init__(self):
        # 按数据类型分组存储连接
        self.connections: Dict[DataType, List[WebSocket]] = {
            DataType.WORD_CLOUD: [],
            DataType.TRENDING: [],
            DataType.NEWS: [],
            DataType.ALL: []  # 接收所有数据的连接
        }

        # 消息处理器
        self.message_handlers: Dict[str, Callable] = {}

    async def connect(self, websocket: WebSocket, data_types: List[DataType]):
        """连接 WebSocket 并订阅数据类型"""
        # ⚠️ 注意：websocket.accept() 已经在路由中调用过了
        # 这里只需要管理连接列表和发送确认消息

        for data_type in data_types:
            self.connections[data_type].append(websocket)

        logger.info(f"WebSocket 连接已建立，订阅: {[dt.value for dt in data_types]}")

        # 发送连接确认
        await self.send_personal_message({
            "type": "connection_established",
            "subscribed_types": [dt.value for dt in data_types],
            "timestamp": datetime.now().isoformat()
        }, websocket)

    def disconnect(self, websocket: WebSocket):
        """断开 WebSocket 连接"""
        for data_type, connections in self.connections.items():
            if websocket in connections:
                connections.remove(websocket)

        logger.info("WebSocket 连接已断开")

    async def send_personal_message(self, message: Dict, websocket: WebSocket):
        """发送个人消息"""
        try:
            await websocket.send_text(json.dumps(message, ensure_ascii=False))
        except Exception as e:
            logger.error(f"发送个人消息失败: {e}")
            self.disconnect(websocket)

    async def broadcast(self, message: Dict, data_type: DataType):
        """广播消息给订阅特定数据类型的连接"""
        if data_type not in self.connections:
            return

        disconnected = []

        for connection in self.connections[data_type]:
            try:
                await connection.send_text(json.dumps(message, ensure_ascii=False))
            except Exception:
                disconnected.append(connection)

        # 清理断开的连接
        for connection in disconnected:
            self.disconnect(connection)

        # 同时发送给订阅 ALL 的连接
        if data_type != DataType.ALL:
            await self.broadcast(message, DataType.ALL)

        if self.connections[data_type]:
            logger.info(f"已广播 {data_type.value} 数据给 {len(self.connections[data_type])} 个连接")

    async def handle_client_message(self, message: str, websocket: WebSocket):
        """处理客户端消息"""
        try:
            data = json.loads(message)
            message_type = data.get("type")

            # 心跳处理
            if message_type == "ping":
                await self.send_personal_message({
                    "type": "pong",
                    "timestamp": datetime.now().isoformat()
                }, websocket)

            # 请求特定数据
            elif message_type == "request_data":
                data_type = data.get("data_type")
                await self.handle_data_request(data_type, websocket)

            # 自定义消息处理器
            elif message_type in self.message_handlers:
                await self.message_handlers[message_type](data, websocket)

        except json.JSONDecodeError:
            await self.send_personal_message({
                "type": "error",
                "message": "无效的 JSON 格式"
            }, websocket)

    async def handle_data_request(self, data_type: str, websocket: WebSocket):
        """处理数据请求"""
        # 这里可以调用相应的服务获取数据
        from .redis_client import RedisClient
        redis_client = RedisClient()

        try:
            if data_type == "word_cloud":
                data = redis_client.get_word_cloud()
                metadata = redis_client.get_metadata()
                await self.send_personal_message({
                    "type": "word_cloud_data",
                    "data": data,
                    "metadata": metadata,
                    "timestamp": datetime.now().isoformat()
                }, websocket)

            elif data_type == "trending":
                data = redis_client.get_trending_keywords()
                metadata = redis_client.get_metadata()
                await self.send_personal_message({
                    "type": "trending_data",
                    "data": data,
                    "metadata": metadata,
                    "timestamp": datetime.now().isoformat()
                }, websocket)

            elif data_type == "news":
                data = redis_client.get_news_feed()
                metadata = redis_client.get_metadata()
                await self.send_personal_message({
                    "type": "news_data",
                    "data": data,
                    "metadata": metadata,
                    "timestamp": datetime.now().isoformat()
                }, websocket)

        except Exception as e:
            await self.send_personal_message({
                "type": "error",
                "message": f"获取 {data_type} 数据失败: {str(e)}"
            }, websocket)

    def register_message_handler(self, message_type: str, handler: Callable):
        """注册自定义消息处理器"""
        self.message_handlers[message_type] = handler


# 全局管理器实例
websocket_manager = ConnectionManager()