# backend/visualization_app/services/scheduler.py
import time
import threading
import schedule
from datetime import datetime, timedelta
from typing import Callable, Any


class DataScheduler:
    """数据调度器 - 用于定时任务（如果需要）
    
    注意：由于数据由其他模块直接写入processed_data命名空间，
    这个调度器主要用于定期检查或触发其他定时任务。
    如果不需要定时任务，可以不启动此调度器。
    """
    
    def __init__(self):
        # 配置项 - 在这里修改时间间隔
        self.UPDATE_INTERVAL_MINUTES = 0.15  # 数据更新间隔（分钟）

        # 运行状态控制
        self._is_running = False
        self._scheduler_thread = None

    def check_data_status(self):
        """检查数据状态（示例任务）"""
        try:
            print(f"\n� [{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] 检查数据状态...")
            # 这里可以添加数据状态检查逻辑
            # 例如：检查Redis中processed_data的更新时间等
            return True
        except Exception as e:
            print(f"❌ [{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] 状态检查失败: {e}")
            return False

    def _run_scheduler(self):
        """运行调度器的内部方法"""
        while self._is_running:
            schedule.run_pending()
            time.sleep(1)

    def start(self, initial_push: bool = True):
        """启动定时任务

        Args:
            initial_push: 是否在启动时立即执行一次检查（保留参数以兼容旧代码）
        """
        if self._is_running:
            print("⚠️ 调度器已经在运行中")
            return

        print("=" * 60)
        print("🚀 启动数据调度器")
        print("=" * 60)
        print(f"📊 检查间隔: {self.UPDATE_INTERVAL_MINUTES} 分钟")
        print("注意：数据由其他模块直接写入processed_data命名空间")
        print("=" * 60)

        # 清除所有现有任务
        schedule.clear()

        # 添加定时任务（如果需要定时检查）
        # schedule.every(self.UPDATE_INTERVAL_MINUTES).minutes.do(self.check_data_status)

        # 启动调度器线程
        self._is_running = True
        self._scheduler_thread = threading.Thread(target=self._run_scheduler, daemon=True)
        self._scheduler_thread.start()

        print(f"✅ 调度器已启动")

    def stop(self):
        """停止定时任务"""
        if not self._is_running:
            print("⚠️ 调度器未在运行")
            return

        self._is_running = False
        schedule.clear()

        if self._scheduler_thread and self._scheduler_thread.is_alive():
            self._scheduler_thread.join(timeout=5)

        print("🛑 数据调度器已停止")

    def trigger_manual_update(self):
        """手动触发更新（保留以兼容旧代码）"""
        print("🎯 手动触发检查...")
        return self.check_data_status()

    def get_status(self):
        """获取调度器状态"""
        status = {
            "is_running": self._is_running,
            "update_interval": self.UPDATE_INTERVAL_MINUTES,
            "next_update": None
        }

        if self._is_running:
            # 获取下一个任务时间
            next_run = schedule.next_run()
            if next_run:
                status["next_update"] = next_run.strftime("%Y-%m-%d %H:%M:%S")

        return status


# 全局调度器实例
_data_scheduler = None


def get_scheduler() -> DataScheduler:
    """获取全局调度器实例"""
    global _data_scheduler
    if _data_scheduler is None:
        _data_scheduler = DataScheduler()
    return _data_scheduler


def run_scheduler_service():
    """运行调度器服务（用于独立运行）"""
    scheduler = get_scheduler()

    try:
        # 启动调度器
        scheduler.start(initial_push=True)

        print("\n📋 调度器命令:")
        print("  - 输入 'status' 查看状态")
        print("  - 输入 'update' 手动更新")
        print("  - 输入 'stop' 停止调度器")
        print("  - 输入 'exit' 退出程序")
        print("  - 输入 'interval 10' 修改间隔为10分钟")

        # 交互式命令循环
        while True:
            try:
                command = input("\n请输入命令: ").strip().lower()

                if command == 'exit':
                    break
                elif command == 'status':
                    status = scheduler.get_status()
                    print(f"\n📊 调度器状态:")
                    print(f"   运行状态: {'运行中' if status['is_running'] else '已停止'}")
                    print(f"   更新间隔: {status['update_interval']} 分钟")
                    print(f"   下次更新: {status['next_update'] or '无'}")
                elif command == 'update':
                    scheduler.trigger_manual_update()
                elif command == 'stop':
                    scheduler.stop()
                elif command.startswith('interval '):
                    try:
                        new_interval = int(command.split()[1])
                        if new_interval > 0:
                            print(f"🔄 修改更新间隔为 {new_interval} 分钟...")
                            scheduler.stop()
                            time.sleep(1)
                            scheduler.UPDATE_INTERVAL_MINUTES = new_interval
                            scheduler.start(initial_push=False)
                        else:
                            print("❌ 间隔时间必须大于0")
                    except (ValueError, IndexError):
                        print("❌ 无效的间隔时间格式，示例: interval 10")
                else:
                    print("❌ 未知命令")

            except KeyboardInterrupt:
                print("\n\n🛑 接收到中断信号，正在停止...")
                break
            except Exception as e:
                print(f"❌ 命令执行错误: {e}")

    finally:
        # 确保调度器停止
        scheduler.stop()
        print("\n👋 调度器服务已退出")


if __name__ == "__main__":
    run_scheduler_service()
