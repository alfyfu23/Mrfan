import pytest
from utils.network import return_field


@pytest.mark.django_db
def test_return_field():
    """测试 return_field 函数"""
    obj_dict = {'id': 1, 'name': 'test', 'email': 'test@example.com', 'age': 25}
    field_list = ['id', 'name', 'email']
    result = return_field(obj_dict, field_list)
    assert result == {'id': 1, 'name': 'test', 'email': 'test@example.com'}
    assert 'age' not in result


@pytest.mark.django_db
def test_return_field_missing_field():
    """测试 return_field 函数缺少字段时抛出异常"""
    obj_dict = {'id': 1, 'name': 'test'}
    field_list = ['id', 'name', 'email']  # email 不存在
    with pytest.raises(AssertionError, match="Field `email` not found"):
        return_field(obj_dict, field_list)



