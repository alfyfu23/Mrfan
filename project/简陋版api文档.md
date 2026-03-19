# API文档

## 用户功能

#### /login

POST方法

- 登陆
- 注册

登陆与注册的区别处理应该由前端完成。

用户登录后注意要同步消息。

#### /profile/info

GET方法

```json
headers = {
    "Authorization": jwt令牌
}
```

获取用户信息，包括：
1. 名称
2. 头像

返回信息
```json
{
    "username": 用户名,
    "avatar": base64编码的image
}
```


#### /profile/change

更改自身的用户名、密码。

## 聊天功能



### 个人消息功能

用户一对一的消息功能
