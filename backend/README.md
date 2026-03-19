# backend后端文档

后端django项目名称为im

## API文档
[API文档](https://gitlab.secoder.net/MrFan/Project/-/blob/main/api%E6%96%87%E6%A1%A3.md)

### code返回码一览

- 0: 成功
- 1001: 注册失败，用户名或密码缺失
- 1002: 注册失败，用户名被占用
- 1003: 登录失败，用户名不存在
- 1004: 登录失败，密码错误

### 其他相关注释

```python
request.method       # 'GET'、'POST'等
request.GET          # GET 参数（字典）
request.POST         # POST 参数（字典）
request.headers      # HTTP 请求头
request.user         # 当前登录用户对象（如果启用了认证系统）
request.body         # 原始请求体（字节串）
request.FILES        # 上传的文件
```
