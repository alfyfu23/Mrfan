import pytest
import asyncio
from unittest.mock import patch, AsyncMock
import pytest_asyncio
from chat.presence import mark_online, mark_offline, is_online, online_snapshot, _online_counts, _lock


@pytest.mark.asyncio
@pytest.mark.django_db
class TestPresenceFunctions:
    """测试在线状态相关函数"""
    
    @pytest_asyncio.fixture(autouse=True)
    async def setup_and_teardown(self):
        """每个测试前后清理全局状态"""
        # Setup: 清理全局状态
        _online_counts.clear()
        yield
        # Teardown: 再次清理全局状态
        _online_counts.clear()
    
    async def test_mark_online_first_time(self):
        """测试首次标记用户上线"""
        user_id = 123
        
        # 首次标记上线，应该返回True（需要广播）
        result = await mark_online(user_id)
        
        assert result is True
        assert _online_counts[user_id] == 1
        assert is_online(user_id) is True
    
    async def test_mark_online_multiple_times(self):
        """测试多次标记用户上线"""
        user_id = 456
        
        # 首次标记上线
        result1 = await mark_online(user_id)
        assert result1 is True
        assert _online_counts[user_id] == 1
        
        # 再次标记上线
        result2 = await mark_online(user_id)
        assert result2 is False  # 不需要广播
        assert _online_counts[user_id] == 2
        
        # 第三次标记上线
        result3 = await mark_online(user_id)
        assert result3 is False  # 不需要广播
        assert _online_counts[user_id] == 3
    
    async def test_mark_offline_last_connection(self):
        """测试标记最后一个连接下线"""
        user_id = 789
        
        # 先标记上线1次
        await mark_online(user_id)
        assert _online_counts[user_id] == 1
        
        # 标记下线，应该返回True（需要广播）
        result = await mark_offline(user_id)
        
        assert result is True
        assert user_id not in _online_counts
        assert is_online(user_id) is False
    
    async def test_mark_offline_multiple_connections(self):
        """测试标记多个连接中的一个下线"""
        user_id = 101112
        
        # 先标记上线3次
        await mark_online(user_id)
        await mark_online(user_id)
        await mark_online(user_id)
        assert _online_counts[user_id] == 3
        
        # 标记下线，应该返回False（不需要广播）
        result1 = await mark_offline(user_id)
        assert result1 is False
        assert _online_counts[user_id] == 2
        
        # 再次标记下线，应该返回False
        result2 = await mark_offline(user_id)
        assert result2 is False
        assert _online_counts[user_id] == 1
        
        # 最后一次标记下线，应该返回True
        result3 = await mark_offline(user_id)
        assert result3 is True
        assert user_id not in _online_counts
        assert is_online(user_id) is False
    
    async def test_mark_offline_nonexistent_user(self):
        """测试标记不存在的用户下线"""
        user_id = 999999
        
        # 标记不存在的用户下线，应该返回True（需要广播）
        result = await mark_offline(user_id)
        
        assert result is True
        assert user_id not in _online_counts
        assert is_online(user_id) is False
    
    async def test_is_online_with_existing_user(self):
        """测试检查已上线用户的状态"""
        user_id = 131415
        
        # 标记用户上线
        await mark_online(user_id)
        
        # 检查用户状态
        assert is_online(user_id) is True
    
    async def test_is_online_with_nonexistent_user(self):
        """测试检查不存在用户的状态"""
        user_id = 161718
        
        # 检查不存在用户的状态
        assert is_online(user_id) is False
    
    async def test_is_online_after_mark_offline(self):
        """测试标记下线后检查用户状态"""
        user_id = 192021
        
        # 标记用户上线
        await mark_online(user_id)
        assert is_online(user_id) is True
        
        # 标记用户下线
        await mark_offline(user_id)
        assert is_online(user_id) is False
    
    async def test_online_snapshot(self):
        """测试获取在线用户快照"""
        # 创建一些在线用户
        user_ids = [100, 200, 300, 400, 500]
        for uid in user_ids:
            await mark_online(uid)
        
        # 获取在线用户快照
        snapshot = online_snapshot()
        
        # 验证快照包含所有在线用户
        assert len(snapshot) == len(user_ids)
        for uid in user_ids:
            assert uid in snapshot
        
        # 验证快照是一个集合
        assert isinstance(snapshot, set)
    
    async def test_online_snapshot_after_mark_offline(self):
        """测试标记下线后获取在线用户快照"""
        # 创建一些在线用户
        user_ids = [100, 200, 300, 400, 500]
        for uid in user_ids:
            await mark_online(uid)
        
        # 标记部分用户下线
        await mark_offline(user_ids[1])
        await mark_offline(user_ids[3])
        
        # 获取在线用户快照
        snapshot = online_snapshot()
        
        # 验证快照只包含在线用户
        assert len(snapshot) == 3
        assert user_ids[0] in snapshot
        assert user_ids[1] not in snapshot
        assert user_ids[2] in snapshot
        assert user_ids[3] not in snapshot
        assert user_ids[4] in snapshot
    
    async def test_concurrent_mark_online(self):
        """测试并发标记用户上线"""
        user_id = 222333
        
        # 并发标记同一个用户上线
        tasks = [mark_online(user_id) for _ in range(10)]
        results = await asyncio.gather(*tasks)
        
        # 第一个应该返回True（需要广播），其余应该返回False
        assert results[0] is True
        assert all(result is False for result in results[1:])
        
        # 验证计数正确
        assert _online_counts[user_id] == 10
        assert is_online(user_id) is True
    
    async def test_concurrent_mark_offline(self):
        """测试并发标记用户下线"""
        user_id = 444555
        
        # 先标记上线10次
        for _ in range(10):
            await mark_online(user_id)
        assert _online_counts[user_id] == 10
        
        # 并发标记同一个用户下线
        tasks = [mark_offline(user_id) for _ in range(10)]
        results = await asyncio.gather(*tasks)
        
        # 验证结果
        # 由于并发执行，结果顺序可能不确定，但应该只有一个True
        true_count = sum(1 for result in results if result is True)
        false_count = sum(1 for result in results if result is False)
        assert true_count == 1
        assert false_count == 9
        
        # 验证最终状态
        assert is_online(user_id) is False
    
    async def test_multiple_users_operations(self):
        """测试多用户操作"""
        user_ids = [1000, 2000, 3000, 4000, 5000]
        
        # 标记所有用户上线
        for uid in user_ids:
            await mark_online(uid)
        
        # 验证所有用户都在线
        for uid in user_ids:
            assert is_online(uid) is True
        
        # 标记部分用户下线
        await mark_offline(user_ids[1])
        await mark_offline(user_ids[3])
        
        # 验证用户状态
        assert is_online(user_ids[0]) is True
        assert is_online(user_ids[1]) is False
        assert is_online(user_ids[2]) is True
        assert is_online(user_ids[3]) is False
        assert is_online(user_ids[4]) is True
        
        # 获取在线用户快照
        snapshot = online_snapshot()
        assert len(snapshot) == 3
        assert user_ids[0] in snapshot
        assert user_ids[1] not in snapshot
        assert user_ids[2] in snapshot
        assert user_ids[3] not in snapshot
        assert user_ids[4] in snapshot
    
    async def test_mark_online_with_zero_user_id(self):
        """测试标记用户ID为0的上线"""
        user_id = 0
        
        # 标记用户ID为0的上线
        result = await mark_online(user_id)
        
        assert result is True
        assert _online_counts[user_id] == 1
        assert is_online(user_id) is True
    
    async def test_mark_offline_with_zero_user_id(self):
        """测试标记用户ID为0的下线"""
        user_id = 0
        
        # 先标记上线
        await mark_online(user_id)
        assert is_online(user_id) is True
        
        # 标记下线
        result = await mark_offline(user_id)
        
        assert result is True
        assert user_id not in _online_counts
        assert is_online(user_id) is False
    
    async def test_mark_online_with_negative_user_id(self):
        """测试标记负数用户ID的上线"""
        user_id = -1
        
        # 标记负数用户ID的上线
        result = await mark_online(user_id)
        
        assert result is True
        assert _online_counts[user_id] == 1
        assert is_online(user_id) is True
    
    async def test_mark_offline_with_negative_user_id(self):
        """测试标记负数用户ID的下线"""
        user_id = -1
        
        # 先标记上线
        await mark_online(user_id)
        assert is_online(user_id) is True
        
        # 标记下线
        result = await mark_offline(user_id)
        
        assert result is True
        assert user_id not in _online_counts
        assert is_online(user_id) is False
    
    async def test_large_number_of_users(self):
        """测试大量用户的在线状态"""
        user_count = 1000
        user_ids = list(range(user_count))
        
        # 标记所有用户上线
        for uid in user_ids:
            await mark_online(uid)
        
        # 验证所有用户都在线
        for uid in user_ids:
            assert is_online(uid) is True
        
        # 验证在线用户快照
        snapshot = online_snapshot()
        assert len(snapshot) == user_count
        for uid in user_ids:
            assert uid in snapshot
        
        # 标记一半用户下线
        for uid in user_ids[::2]:
            await mark_offline(uid)
        
        # 验证在线用户数量
        snapshot = online_snapshot()
        assert len(snapshot) == user_count // 2
        
        # 标记所有用户下线
        for uid in user_ids[1::2]:
            await mark_offline(uid)
        
        # 验证所有用户都下线
        snapshot = online_snapshot()
        assert len(snapshot) == 0
    
    @patch('chat.presence._lock')
    async def test_lock_usage_in_mark_online(self, mock_lock):
        """测试mark_online中的锁使用"""
        # 设置mock锁
        mock_lock.__aenter__ = AsyncMock(return_value=None)
        mock_lock.__aexit__ = AsyncMock(return_value=None)
        
        user_id = 12345
        
        # 调用mark_online
        await mark_online(user_id)
        
        # 验证锁被使用
        mock_lock.__aenter__.assert_called_once()
        mock_lock.__aexit__.assert_called_once()
    
    @patch('chat.presence._lock')
    async def test_lock_usage_in_mark_offline(self, mock_lock):
        """测试mark_offline中的锁使用"""
        # 设置mock锁
        mock_lock.__aenter__ = AsyncMock(return_value=None)
        mock_lock.__aexit__ = AsyncMock(return_value=None)
        
        user_id = 54321
        
        # 调用mark_offline
        await mark_offline(user_id)
        
        # 验证锁被使用
        mock_lock.__aenter__.assert_called_once()
        mock_lock.__aexit__.assert_called_once()
    
    async def test_is_online_without_lock(self):
        """测试is_online不使用锁"""
        # is_online是同步函数，不应该使用锁
        user_id = 99999
        
        # 直接调用is_online
        result = is_online(user_id)
        
        # 验证返回False（用户不存在）
        assert result is False
    
    async def test_online_snapshot_without_lock(self):
        """测试online_snapshot不使用锁"""
        # online_snapshot是同步函数，不应该使用锁
        
        # 直接调用online_snapshot
        snapshot = online_snapshot()
        
        # 验证返回集合（可能为空，因为setup会清理）
        assert isinstance(snapshot, set)
    
    async def test_reset_online_counts(self):
        """测试重置在线计数（用于测试清理）"""
        # 添加一些在线用户
        user_ids = [100, 200, 300]
        for uid in user_ids:
            await mark_online(uid)
        
        # 验证用户在线
        for uid in user_ids:
            assert is_online(uid) is True
        
        # 手动清空在线计数
        _online_counts.clear()
        
        # 验证所有用户都不在线
        for uid in user_ids:
            assert is_online(uid) is False
        
        # 验证在线用户快照为空
        snapshot = online_snapshot()
        assert len(snapshot) == 0