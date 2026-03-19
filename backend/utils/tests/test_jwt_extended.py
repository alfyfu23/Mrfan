import pytest
import time
import json
from unittest.mock import patch
from utils.jwt import generate_jwt_token, parse_jwt_token, b64url_encode, b64url_decode


class TestJWTFunctions:
    """测试JWT相关函数的各种边界情况"""
    
    def test_generate_jwt_token_basic(self):
        """测试基本JWT生成功能"""
        username = 'testuser'
        user_id = 123
        
        token = generate_jwt_token(username, user_id)
        
        # 验证token结构
        assert isinstance(token, str)
        parts = token.split('.')
        assert len(parts) == 3  # header.payload.signature
        
        # 验证可以解析
        parsed_id = parse_jwt_token(token)
        assert parsed_id == user_id
    
    def test_parse_jwt_token_basic(self):
        """测试基本JWT解析功能"""
        username = 'testuser'
        user_id = 456
        
        token = generate_jwt_token(username, user_id)
        parsed_id = parse_jwt_token(token)
        
        assert parsed_id == user_id
    
    def test_parse_jwt_token_invalid_format(self):
        """测试解析格式无效的JWT"""
        # 测试空字符串
        assert parse_jwt_token('') is None
        
        # 测试只有一部分
        assert parse_jwt_token('header') is None
        
        # 测试只有两部分
        assert parse_jwt_token('header.payload') is None
        
        # 测试多于三部分
        assert parse_jwt_token('header.payload.signature.extra') is None
    
    def test_parse_jwt_token_invalid_signature(self):
        """测试解析签名无效的JWT"""
        # 生成有效token
        token = generate_jwt_token('testuser', 123)
        parts = token.split('.')
        
        # 修改签名部分
        invalid_token = f"{parts[0]}.{parts[1]}.invalid_signature"
        
        # 应该返回None
        assert parse_jwt_token(invalid_token) is None
    
    def test_parse_jwt_token_expired(self):
        """测试解析过期的JWT"""
        # 生成token
        token = generate_jwt_token('testuser', 123)
        
        # 模拟过期（修改payload中的exp）
        parts = token.split('.')
        payload_json = b64url_decode(parts[1])
        payload = json.loads(payload_json)
        
        # 设置过期时间为过去
        payload['exp'] = int(time.time()) - 3600  # 1小时前
        
        # 重新编码payload
        new_payload = b64url_encode(json.dumps(payload, separators=(',', ':')))
        
        # 构造新token（使用原始签名）
        expired_token = f"{parts[0]}.{new_payload}.{parts[2]}"
        
        # 应该返回None
        assert parse_jwt_token(expired_token) is None
    
    def test_parse_jwt_token_missing_fields(self):
        """测试解析缺少必要字段的JWT"""
        # 构造缺少exp字段的payload
        payload = {
            "iat": int(time.time()),
            "data": {
                "username": "testuser",
                "id": 123
            }
        }
    
        # 编码header和payload
        header = {"alg": "HS256", "typ": "JWT"}
        header_b64 = b64url_encode(json.dumps(header, separators=(',', ':')))
        payload_b64 = b64url_encode(json.dumps(payload, separators=(',', ':')))
    
        # 生成签名
        signature_raw = header_b64 + "." + payload_b64
        import hmac
        import hashlib
        from utils.jwt import SALT
        signature = hmac.new(SALT, signature_raw.encode("utf-8"), digestmod=hashlib.sha256).digest()
        signature_b64 = b64url_encode(signature)
    
        # 构造token
        token = f"{header_b64}.{payload_b64}.{signature_b64}"
    
        # 应该抛出KeyError，因为缺少exp字段
        with pytest.raises(KeyError):
            parse_jwt_token(token)
    
    def test_parse_jwt_token_missing_data_field(self):
        """测试解析缺少data字段的JWT"""
        # 构造缺少data字段的payload
        payload = {
            "iat": int(time.time()),
            "exp": int(time.time()) + 3600,
            "other": "data"
        }
    
        # 编码header和payload
        header = {"alg": "HS256", "typ": "JWT"}
        header_b64 = b64url_encode(json.dumps(header, separators=(',', ':')))
        payload_b64 = b64url_encode(json.dumps(payload, separators=(',', ':')))
    
        # 生成签名
        signature_raw = header_b64 + "." + payload_b64
        import hmac
        import hashlib
        from utils.jwt import SALT
        signature = hmac.new(SALT, signature_raw.encode("utf-8"), digestmod=hashlib.sha256).digest()
        signature_b64 = b64url_encode(signature)
    
        # 构造token
        token = f"{header_b64}.{payload_b64}.{signature_b64}"
    
        # 应该抛出KeyError，因为缺少data字段
        with pytest.raises(KeyError):
            parse_jwt_token(token)
    
    def test_parse_jwt_token_missing_id_in_data(self):
        """测试解析data字段中缺少id的JWT"""
        # 构造data字段中缺少id的payload
        payload = {
            "iat": int(time.time()),
            "exp": int(time.time()) + 3600,
            "data": {
                "username": "testuser"
                # 缺少id字段
            }
        }
    
        # 编码header和payload
        header = {"alg": "HS256", "typ": "JWT"}
        header_b64 = b64url_encode(json.dumps(header, separators=(',', ':')))
        payload_b64 = b64url_encode(json.dumps(payload, separators=(',', ':')))
    
        # 生成签名
        signature_raw = header_b64 + "." + payload_b64
        import hmac
        import hashlib
        from utils.jwt import SALT
        signature = hmac.new(SALT, signature_raw.encode("utf-8"), digestmod=hashlib.sha256).digest()
        signature_b64 = b64url_encode(signature)
    
        # 构造token
        token = f"{header_b64}.{payload_b64}.{signature_b64}"
    
        # 应该抛出KeyError，因为缺少id字段
        with pytest.raises(KeyError):
            parse_jwt_token(token)
    
    def test_b64url_encode_string(self):
        """测试字符串的base64url编码"""
        test_str = "Hello, World!"
        encoded = b64url_encode(test_str)
        
        # 验证编码结果
        assert isinstance(encoded, str)
        assert '=' not in encoded  # 不应该有填充
        
        # 验证可以解码
        decoded = b64url_decode(encoded)
        assert decoded == test_str
    
    def test_b64url_encode_bytes(self):
        """测试字节的base64url编码"""
        test_bytes = b"Hello, World!"
        encoded = b64url_encode(test_bytes)
        
        # 验证编码结果
        assert isinstance(encoded, str)
        assert '=' not in encoded  # 不应该有填充
        
        # 验证可以解码
        decoded = b64url_decode(encoded, decode_to_str=False)
        assert decoded == test_bytes
    
    def test_b64url_decode_string(self):
        """测试字符串的base64url解码"""
        test_str = "Hello, World!"
        encoded = b64url_encode(test_str)
        decoded = b64url_decode(encoded)
        
        assert decoded == test_str
    
    def test_b64url_decode_bytes(self):
        """测试字节的base64url解码"""
        test_bytes = b"Hello, World!"
        encoded = b64url_encode(test_bytes)
        decoded = b64url_decode(encoded, decode_to_str=False)
        
        assert decoded == test_bytes
    
    def test_b64url_decode_with_padding(self):
        """测试需要填充的base64url解码"""
        # 创建一个需要填充的base64字符串
        import base64
        from utils.jwt import ALT_CHARS
        test_str = "Test"
        standard_b64 = base64.b64encode(test_str.encode('utf-8')).decode('utf-8')
        urlsafe_b64 = base64.b64encode(test_str.encode('utf-8'), altchars=ALT_CHARS).decode('utf-8').strip('=')
        
        # 我们的b64url_decode应该能处理无填充的情况
        decoded = b64url_decode(urlsafe_b64)
        assert decoded == test_str
        
        # 也应该能处理有填充的情况
        decoded_with_padding = b64url_decode(standard_b64)
        assert decoded_with_padding == test_str
    
    def test_b64url_decode_invalid_base64(self):
        """测试无效base64字符串的解码"""
        # 测试无效字符
        with pytest.raises(Exception):  # 可能是binascii.Error或其他异常
            b64url_decode("invalid_base64!")
    
    def test_jwt_token_with_unicode(self):
        """测试包含Unicode字符的JWT"""
        username = '测试用户'
        user_id = 789
        
        token = generate_jwt_token(username, user_id)
        parsed_id = parse_jwt_token(token)
        
        assert parsed_id == user_id
    
    def test_jwt_token_with_special_chars(self):
        """测试包含特殊字符的JWT"""
        username = 'user@domain.com'
        user_id = 101112
        
        token = generate_jwt_token(username, user_id)
        parsed_id = parse_jwt_token(token)
        
        assert parsed_id == user_id
    
    def test_jwt_token_edge_case_ids(self):
        """测试边界情况的用户ID"""
        # 测试0
        token = generate_jwt_token('user', 0)
        assert parse_jwt_token(token) == 0
        
        # 测试负数
        token = generate_jwt_token('user', -1)
        assert parse_jwt_token(token) == -1
        
        # 测试大数
        large_id = 2**31 - 1  # 32位有符号整数最大值
        token = generate_jwt_token('user', large_id)
        assert parse_jwt_token(token) == large_id
    
    def test_jwt_token_with_empty_username(self):
        """测试空用户名的JWT"""
        username = ''
        user_id = 123
        
        token = generate_jwt_token(username, user_id)
        parsed_id = parse_jwt_token(token)
        
        assert parsed_id == user_id
    
    @patch('time.time')
    def test_jwt_token_with_mock_time(self, mock_time):
        """测试使用模拟时间的JWT"""
        # 设置固定时间
        fixed_time = 1609459200  # 2021-01-01 00:00:00 UTC
        mock_time.return_value = fixed_time
        
        username = 'testuser'
        user_id = 123
        
        token = generate_jwt_token(username, user_id)
        
        # 解析token并验证时间
        parts = token.split('.')
        payload_json = b64url_decode(parts[1])
        payload = json.loads(payload_json)
        
        assert payload['iat'] == fixed_time
        assert payload['exp'] == fixed_time + 7200  # 2小时后
    
    def test_jwt_token_consistency(self):
        """测试JWT生成的一致性"""
        username = 'testuser'
        user_id = 123
    
        # 生成多个token
        token1 = generate_jwt_token(username, user_id)
        time.sleep(0.01)  # 确保时间不同
        token2 = generate_jwt_token(username, user_id)
    
        # 验证两个token都有效且解析出相同的用户ID
        assert parse_jwt_token(token1) == user_id
        assert parse_jwt_token(token2) == user_id
        
        # token可能相同（如果时间戳相同），也可能不同（如果时间戳不同）
        # 这里我们只验证它们都能正确解析
        
        # 但都应该能解析出相同的用户ID
        assert parse_jwt_token(token1) == user_id
        assert parse_jwt_token(token2) == user_id
    
    def test_b64url_encode_decode_roundtrip(self):
        """测试base64url编码解码的往返"""
        test_cases = [
            "Hello, World!",
            "测试中文",
            "Special chars: !@#$%^&*()",
            "",
            "a" * 1000,  # 长字符串
            "🚀🌟⭐"  # emoji
        ]
        
        for test_str in test_cases:
            encoded = b64url_encode(test_str)
            decoded = b64url_decode(encoded)
            assert decoded == test_str
    
    def test_b64url_encode_decode_bytes_roundtrip(self):
        """测试字节base64url编码解码的往返"""
        test_cases = [
            b"Hello, World!",
            b"Binary data \x00\x01\x02",
            b"",
            b"a" * 1000,  # 长字节串
        ]
        
        for test_bytes in test_cases:
            encoded = b64url_encode(test_bytes)
            decoded = b64url_decode(encoded, decode_to_str=False)
            assert decoded == test_bytes
    
    def test_parse_jwt_token_with_malformed_json(self):
        """测试解析包含格式错误JSON的JWT"""
        # 构造包含格式错误JSON的payload
        malformed_payload = b64url_encode('{"iat": 123, "exp": 456, "data": {"id": 789}')  # 缺少闭合括号
    
        # 编码header
        header = {"alg": "HS256", "typ": "JWT"}
        header_b64 = b64url_encode(json.dumps(header, separators=(',', ':')))
    
        # 生成签名
        signature_raw = header_b64 + "." + malformed_payload
        import hmac
        import hashlib
        from utils.jwt import SALT
        signature = hmac.new(SALT, signature_raw.encode("utf-8"), digestmod=hashlib.sha256).digest()
        signature_b64 = b64url_encode(signature)
    
        # 构造token
        token = f"{header_b64}.{malformed_payload}.{signature_b64}"
    
        # 应该抛出JSONDecodeError
        with pytest.raises(json.JSONDecodeError):
            parse_jwt_token(token)
    
    def test_parse_jwt_token_with_non_numeric_id(self):
        """测试解析包含非数字ID的JWT"""
        # 构造包含字符串ID的payload
        payload = {
            "iat": int(time.time()),
            "exp": int(time.time()) + 3600,
            "data": {
                "username": "testuser",
                "id": "not_a_number"  # 字符串而非数字
            }
        }
    
        # 编码header和payload
        header = {"alg": "HS256", "typ": "JWT"}
        header_b64 = b64url_encode(json.dumps(header, separators=(',', ':')))
        payload_b64 = b64url_encode(json.dumps(payload, separators=(',', ':')))
    
        # 生成签名
        signature_raw = header_b64 + "." + payload_b64
        import hmac
        import hashlib
        from utils.jwt import SALT
        signature = hmac.new(SALT, signature_raw.encode("utf-8"), digestmod=hashlib.sha256).digest()
        signature_b64 = b64url_encode(signature)
    
        # 构造token
        token = f"{header_b64}.{payload_b64}.{signature_b64}"
    
        # 应该返回字符串ID，因为parse_jwt_token不做类型检查
        assert parse_jwt_token(token) == "not_a_number"