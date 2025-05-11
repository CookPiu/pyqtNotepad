# wangEditor 图片上传功能说明

## 功能概述

本文档说明了如何在 wangEditor 中使用图片上传功能。由于编辑器运行在 PyQt6 的 WebEngine 环境中，图片上传通过 WebChannel 与 Python 后端通信实现，无需额外的 HTTP 服务器。

## 实现原理

1. 前端（JavaScript）：
   - 使用 wangEditor 的自定义上传功能 `customUpload`
   - 将图片转换为 base64 格式通过 WebChannel 传输给 Python 后端
   - 接收 Python 返回的图片 URL 并插入到编辑器中

2. 后端（Python）：
   - 接收 base64 格式的图片数据
   - 解码并保存到指定目录
   - 返回图片的 URL（本地文件路径）给前端

## 使用方法

### 1. 初始化 WangEditor

```python
from wang_editor import WangEditor

# 创建编辑器实例，指定图片上传目录
upload_dir = "path/to/uploads"
editor = WangEditor(upload_dir=upload_dir)
```

### 2. 设置上传目录

```python
# 可以在创建后修改上传目录
editor.setUploadDir("path/to/new/uploads")
```

### 3. 获取包含图片的内容

```python
def handle_content(html):
    # 处理包含图片的HTML内容
    print(html)

# 获取编辑器内容
editor.getHtml(handle_content)
```

## 注意事项

1. 上传目录必须存在且可写入，如不存在会自动创建
2. 图片使用 UUID 重命名，避免文件名冲突
3. 图片 URL 使用 `file://` 协议，仅适用于本地应用
4. 大图片可能导致性能问题，建议添加图片大小限制

## 示例代码

完整示例请参考 `example.py` 文件，展示了如何创建编辑器并处理图片上传。

## 自定义配置

如需修改上传行为，可以编辑以下文件：

1. `editor.html` - 修改前端上传逻辑
2. `wang_editor.py` - 修改后端处理逻辑

## 故障排除

如果图片上传失败，请检查：

1. 上传目录是否存在且有写入权限
2. 控制台是否有错误信息
3. WebChannel 是否正确初始化
4. 图片格式是否支持