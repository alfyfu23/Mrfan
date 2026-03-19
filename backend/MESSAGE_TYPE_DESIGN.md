# 消息类型设计说明

## 设计思路

在 `Message` 模型中添加 `type` 字段来区分消息类型，所有类型的消息（文本、图片等）都使用统一的 `Message` 模型存储。

## Message 模型字段

```python
class Message(models.Model):
    conversation = ForeignKey(Conversation)  # 所属会话
    member = ForeignKey(Member)              # 发送者
    type = CharField(max_length=20)          # 消息类型：text/image/file/video/audio
    content = TextField(blank=True)          # 消息内容
    time = DateTimeField(auto_now_add=True)  # 发送时间
    is_edited = BooleanField(default=False)  # 是否编辑过
    valid = BooleanField(default=True)       # 是否有效
    read_list = ManyToManyField(Member)      # 已读列表
    delete_list = ManyToManyField(Member)    # 删除列表
```

## 消息类型 (type 字段)

| 类型 | 值 | content 字段内容 | 说明 |
|------|-----|------------------|------|
| 文本消息 | `text` | 文本内容 | 普通文字消息 |
| 图片消息 | `image` | 图片URL | 图片的完整访问路径 |
| 表情消息 | `emoji` | 表情符号 | Unicode 表情符号，如 😊、👍、❤️ |
| 视频消息 | `video` | 视频URL | 预留：视频播放地址 |
| 音频消息 | `audio` | 音频URL | 预留：音频文件地址 |

## 使用示例

### 1. 发送文本消息
```python
message = Message.objects.create(
    conversation=conversation,
    member=member,
    type='text',
    content='你好，这是一条文本消息'
)
```

### 2. 发送图片消息
```python
# 假设图片已经上传到服务器或CDN
image_url = 'https://example.com/images/photo.jpg'

message = Message.objects.create(
    conversation=conversation,
    member=member,
    type='image',
    content=image_url  # 直接存储图片URL
)
```

### 3. 发送表情消息
```python
# 发送一个表情符号
emoji_content = '😊'  # 可以是任何 Unicode 表情

message = Message.objects.create(
    conversation=conversation,
    member=member,
    type='emoji',
    content=emoji_content  # 直接存储表情符号
)
```

### 4. 前端处理
```javascript
// 前端根据 type 字段渲染不同的消息类型
messages.forEach(msg => {
    if (msg.type === 'text') {
        // 渲染文本消息
        renderTextMessage(msg.content);
    } else if (msg.type === 'image') {
        // 渲染图片消息
        renderImageMessage(msg.content);
    } else if (msg.type === 'emoji') {
        // 渲染表情消息（可以设置较大的字体）
        renderEmojiMessage(msg.content);
    }
});
```

### 5. 查询特定类型的消息
```python
# 查询某个会话的所有图片消息
image_messages = Message.objects.filter(
    conversation=conversation,
    type='image',
    valid=True
).order_by('-time')

# 查询某个会话的所有表情消息
emoji_messages = Message.objects.filter(
    conversation=conversation,
    type='emoji',
    valid=True
).order_by('-time')
```

## 测试数据说明 (initial_data.json)

fixture 文件包含以下测试消息：

**文本消息：**
- Message #100: "樱岛麻衣和喜多川海梦。"
- Message #101: "电次和玛奇玛。"
- Message #102: "阿库娅和惠惠。"
- Message #103: "看看这张图片"
- Message #105: "哇，好看！"
- Message #107: "这张风景照真不错"
- Message #108: "群里发个图"
- Message #110: "收到！"
- Message #112: "测试消息"
- Message #114: "好可爱的猫咪！"

**图片消息：**
- Message #104: https://example.com/images/anime_character.jpg
- Message #106: https://example.com/images/landscape.png
- Message #109: https://example.com/images/group_photo.jpg
- Message #111: https://example.com/images/meme_funny.gif
- Message #113: https://example.com/images/cat_cute.jpg

## 设计优势

### 1. **简洁统一**
- 所有消息类型使用同一个模型和表
- 不需要额外的关联表
- 数据结构简单清晰

### 2. **易于扩展**
- 添加新的消息类型只需在 choices 中增加选项
- 不需要修改数据库结构
- content 字段可以灵活存储不同类型的数据

### 3. **前端友好**
- 前端只需判断 type 字段即可决定渲染方式
- 图片大小、缩略图等完全由前端控制
- 减少后端处理负担

### 4. **性能优良**
- 查询简单，不需要 JOIN 多张表
- 索引优化方便
- 支持按类型快速筛选

## 前端渲染建议

### 图片消息处理
```javascript
function renderImageMessage(imageUrl) {
    const img = document.createElement('img');
    img.src = imageUrl;
    
    // 前端控制图片显示大小
    img.style.maxWidth = '300px';
    img.style.maxHeight = '300px';
    
    // 懒加载
    img.loading = 'lazy';
    
    // 点击查看大图
    img.onclick = () => showFullImage(imageUrl);
    
    // 缩略图可以通过 URL 参数实现
    // 例如：imageUrl + '?thumbnail=true'
    
    return img;
}
```

### 图片加载优化
```javascript
// 使用 Intersection Observer 实现懒加载
const observer = new IntersectionObserver((entries) => {
    entries.forEach(entry => {
        if (entry.isIntersecting) {
            const img = entry.target;
            img.src = img.dataset.src;
            observer.unobserve(img);
        }
    });
});

// 缩略图策略
function getImageUrl(url, thumbnail = false) {
    if (thumbnail) {
        // 可以使用 CDN 的缩略图功能
        return url + '?x-oss-process=image/resize,w_200';
    }
    return url;
}
```

## 数据库迁移

### 1. 生成迁移文件
```bash
python manage.py makemigrations chat
```

### 2. 应用迁移
```bash
python manage.py migrate chat
```

### 3. 加载测试数据
```bash
python manage.py loaddata chat/fixtures/initial_data.json
```

## 注意事项

1. **URL 存储**：确保存储的是完整的可访问 URL
2. **前端验证**：上传前在前端验证图片格式和大小
3. **安全性**：URL 应该包含防盗链或签名机制
4. **CDN 使用**：建议使用 CDN 加速图片访问
5. **类型扩展**：未来可以添加更多类型如 emoji、位置、名片等
