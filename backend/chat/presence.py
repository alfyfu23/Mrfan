import asyncio
from typing import Dict, Set


# 维护用户在线连接计数；同一用户多端登录只在计数从 0->1 或 1->0 时广播状态
_online_counts: Dict[int, int] = {}
_lock = asyncio.Lock()


async def mark_online(user_id: int) -> bool:
    """标记用户上线，返回是否是首次上线（需要广播）。"""
    async with _lock:
        prev = _online_counts.get(user_id, 0)
        _online_counts[user_id] = prev + 1
        return prev == 0


async def mark_offline(user_id: int) -> bool:
    """标记用户下线，返回是否已完全离线（需要广播）。"""
    async with _lock:
        prev = _online_counts.get(user_id, 0)
        if prev <= 1:
            _online_counts.pop(user_id, None)
            return True
        _online_counts[user_id] = prev - 1
        return False


def is_online(user_id: int) -> bool:
    """同步读取用户是否在线，用于 HTTP API。"""
    return _online_counts.get(user_id, 0) > 0


def online_snapshot() -> Set[int]:
    """返回当前在线用户快照。"""
    return set(_online_counts.keys())
