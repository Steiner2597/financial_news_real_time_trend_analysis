"""
信号处理器
处理程序退出信号（SIGINT, SIGTERM）
"""
import signal
import logging
from typing import Callable, Optional

logger = logging.getLogger(__name__)


class SignalHandler:
    """信号处理器"""
    
    def __init__(self, stop_callback: Callable[[], None]):
        """
        初始化信号处理器
        
        Args:
            stop_callback: 停止回调函数
        """
        self.stop_callback = stop_callback
        self._original_sigint: Optional[signal.Handlers] = None
        self._original_sigterm: Optional[signal.Handlers] = None
    
    def setup(self):
        """设置信号处理"""
        # 保存原始处理器
        self._original_sigint = signal.signal(signal.SIGINT, self._signal_handler)
        self._original_sigterm = signal.signal(signal.SIGTERM, self._signal_handler)
        logger.debug("✓ 信号处理器已设置")
    
    def _signal_handler(self, signum, frame):
        """
        处理退出信号
        
        Args:
            signum: 信号编号
            frame: 当前栈帧
        """
        signal_name = signal.Signals(signum).name
        logger.info(f"\n\n⚠️  收到退出信号 ({signal_name})，正在优雅关闭...")
        self.stop_callback()
    
    def restore(self):
        """恢复原始信号处理器"""
        if self._original_sigint is not None:
            signal.signal(signal.SIGINT, self._original_sigint)
        if self._original_sigterm is not None:
            signal.signal(signal.SIGTERM, self._original_sigterm)
        logger.debug("✓ 信号处理器已恢复")
