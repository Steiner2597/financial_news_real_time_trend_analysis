# backend/app/routes/websocket_routes.py
from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from typing import List
import json
import logging
import traceback

# 设置详细日志
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

from ..services.websocket_manager import (
    websocket_manager,
    DataType
)

router = APIRouter()


@router.websocket("/ws/wordcloud")
async def websocket_wordcloud(websocket: WebSocket):
    """词云数据 WebSocket"""
    print("=" * 50)
    print("🔄 接收到词云数据 WebSocket 连接请求...")
    print(f"客户端: {websocket.client}")

    try:
        # 第一步：尝试接受连接
        print("1. 尝试执行 websocket.accept()...")
        await websocket.accept()
        print("✅ websocket.accept() 成功")

        # 第二步：使用统一管理器连接
        print("2. 尝试连接到 websocket_manager...")
        await websocket_manager.connect(websocket, [DataType.WORD_CLOUD])
        print("✅ websocket_manager.connect() 成功")
        print("🎉 词云 WebSocket 连接完全建立！")

        try:
            while True:
                print("⏳ 等待客户端消息...")
                data = await websocket.receive_text()
                print(f"📨 收到客户端消息: {data}")
                await websocket_manager.handle_client_message(data, websocket)
        except WebSocketDisconnect:
            print("🔌 WebSocket 连接正常断开")
            websocket_manager.disconnect(websocket)
        except Exception as e:
            print(f"❌ WebSocket 消息处理错误: {e}")
            traceback.print_exc()

    except Exception as e:
        print(f"💥 WebSocket 连接建立失败: {e}")
        print("完整错误信息:")
        traceback.print_exc()
        # 尝试关闭连接
        try:
            await websocket.close()
        except:
            pass


@router.websocket("/ws/trending")
async def websocket_trending(websocket: WebSocket):
    """趋势数据 WebSocket"""
    print("=" * 50)
    print("🔄 接收到趋势数据 WebSocket 连接请求...")
    print(f"客户端: {websocket.client}")

    try:
        print("1. 尝试执行 websocket.accept()...")
        await websocket.accept()
        print("✅ websocket.accept() 成功")

        print("2. 尝试连接到 websocket_manager...")
        await websocket_manager.connect(websocket, [DataType.TRENDING])
        print("✅ websocket_manager.connect() 成功")
        print("🎉 趋势数据 WebSocket 连接完全建立！")

        try:
            while True:
                data = await websocket.receive_text()
                print(f"📨 收到趋势数据客户端消息: {data}")
                await websocket_manager.handle_client_message(data, websocket)
        except WebSocketDisconnect:
            print("🔌 趋势数据 WebSocket 连接正常断开")
            websocket_manager.disconnect(websocket)
        except Exception as e:
            print(f"❌ 趋势数据 WebSocket 消息处理错误: {e}")
            traceback.print_exc()

    except Exception as e:
        print(f"💥 趋势数据 WebSocket 连接建立失败: {e}")
        traceback.print_exc()
        try:
            await websocket.close()
        except:
            pass


@router.websocket("/ws/news")
async def websocket_news(websocket: WebSocket):
    """新闻数据 WebSocket"""
    print("=" * 50)
    print("🔄 接收到新闻数据 WebSocket 连接请求...")
    print(f"客户端: {websocket.client}")

    try:
        print("1. 尝试执行 websocket.accept()...")
        await websocket.accept()
        print("✅ websocket.accept() 成功")

        print("2. 尝试连接到 websocket_manager...")
        await websocket_manager.connect(websocket, [DataType.NEWS])
        print("✅ websocket_manager.connect() 成功")
        print("🎉 新闻数据 WebSocket 连接完全建立！")

        try:
            while True:
                data = await websocket.receive_text()
                print(f"📨 收到新闻数据客户端消息: {data}")
                await websocket_manager.handle_client_message(data, websocket)
        except WebSocketDisconnect:
            print("🔌 新闻数据 WebSocket 连接正常断开")
            websocket_manager.disconnect(websocket)
        except Exception as e:
            print(f"❌ 新闻数据 WebSocket 消息处理错误: {e}")
            traceback.print_exc()

    except Exception as e:
        print(f"💥 新闻数据 WebSocket 连接建立失败: {e}")
        traceback.print_exc()
        try:
            await websocket.close()
        except:
            pass


@router.websocket("/ws/all")
async def websocket_all_data(websocket: WebSocket):
    """所有数据的 WebSocket"""
    print("=" * 50)
    print("🔄 接收到所有数据 WebSocket 连接请求...")
    print(f"客户端: {websocket.client}")

    try:
        print("1. 尝试执行 websocket.accept()...")
        await websocket.accept()
        print("✅ websocket.accept() 成功")

        print("2. 尝试连接到 websocket_manager...")
        await websocket_manager.connect(websocket, [DataType.ALL])
        print("✅ websocket_manager.connect() 成功")
        print("🎉 所有数据 WebSocket 连接完全建立！")

        try:
            while True:
                data = await websocket.receive_text()
                print(f"📨 收到所有数据客户端消息: {data}")
                await websocket_manager.handle_client_message(data, websocket)
        except WebSocketDisconnect:
            print("🔌 所有数据 WebSocket 连接正常断开")
            websocket_manager.disconnect(websocket)
        except Exception as e:
            print(f"❌ 所有数据 WebSocket 消息处理错误: {e}")
            traceback.print_exc()

    except Exception as e:
        print(f"💥 所有数据 WebSocket 连接建立失败: {e}")
        traceback.print_exc()
        try:
            await websocket.close()
        except:
            pass
