# MM-Wiki CLI Skill

MM-Wiki CLI 提供了一个命令行接口，用于通过 HTTP API 管理已部署的 MM-Wiki 系统。

## 概述

此 Skill 允许 AI Agent 通过 `mmwiki-cli` 工具与 MM-Wiki 服务器进行交互，执行用户管理、空间管理、文档管理等操作。

## 安装

### 构建 CLI 工具

```bash
cd agent/cli
go mod tidy
go build -o mmwiki-cli ./
```

### 添加到 PATH

```bash
# Linux/Mac
mv mmwiki-cli /usr/local/bin/
chmod +x /usr/local/bin/mmwiki-cli

# Or use directly
./mmwiki-cli --help
```

## 认证

MM-Wiki CLI 使用 Session Cookie 进行认证。首次使用需要先登录：

```bash
mmwiki-cli login --url http://wiki.example.com:8081 --username admin --password yourpassword
```

登录成功后会保存 session，后续命令无需重复提供认证信息。

### 检查登录状态

```bash
mmwiki-cli status
```

### 登出

```bash
mmwiki-cli logout
```

## 命令参考

### 用户管理

#### 列出用户

```bash
mmwiki-cli user list
mmwiki-cli user list --limit 50 --offset 0
mmwiki-cli user list --search "john"
```

#### 获取用户信息

```bash
mmwiki-cli user get --id 1
```

#### 创建用户

```bash
mmwiki-cli user create \
  --username "newuser" \
  --password "secret123" \
  --name "New User" \
  --email "user@example.com" \
  --phone "1234567890" \
  --role 3
```

角色 ID：
- `1` - 超级管理员
- `2` - 管理员  
- `3` - 普通用户

#### 更新用户

```bash
mmwiki-cli user update --id 2 --name "Updated Name" --email "new@example.com"
```

#### 删除用户

```bash
mmwiki-cli user delete --id 2
```

### 空间管理

#### 列出空间

```bash
mmwiki-cli space list
mmwiki-cli space list --limit 50
```

#### 获取空间信息

```bash
mmwiki-cli space get --id 1
```

#### 创建空间

```bash
mmwiki-cli space create \
  --name "Project Wiki" \
  --description "Documentation for the project" \
  --tags "project,docs" \
  --level public \
  --owner 1
```

访问级别：
- `public` - 公开访问
- `private` - 私有空间

#### 更新空间

```bash
mmwiki-cli space update --id 1 --name "New Name" --description "Updated desc"
```

#### 删除空间

```bash
mmwiki-cli space delete --id 1
```

### 文档管理

#### 列出文档

```bash
mmwiki-cli doc list --space 1
mmwiki-cli doc list --space 1 --parent 0
```

#### 查看文档树

```bash
mmwiki-cli doc tree --space 1
```

#### 创建文档

```bash
# 创建页面
mmwiki-cli doc create --space 1 --parent 0 --name "New Page" --type page

# 创建目录
mmwiki-cli doc create --space 1 --parent 0 --name "New Folder" --type dir
```

#### 读取文档内容

```bash
# 输出到控制台
mmwiki-cli doc read --id 123

# 输出到文件
mmwiki-cli doc read --id 123 --output /path/to/file.md
```

#### 写入文档内容

```bash
# 从字符串写入
mmwiki-cli doc write --id 123 --content "# New Content"

# 从文件写入
mmwiki-cli doc write --id 123 --file /path/to/content.md

# 带注释
mmwiki-cli doc write --id 123 --file content.md --comment "Updated section 1"
```

#### 移动文档

```bash
mmwiki-cli doc move --id 123 --target 456 --type inner
```

移动类型：
- `inner` - 移动到目标内部
- `inner_next` - 移动到目标内部的下一个位置
- `next` - 移动到目标之后
- `prev` - 移动到目标之前

#### 更新文档元数据

```bash
mmwiki-cli doc update --id 123 --name "New Document Name"
```

#### 删除文档

```bash
mmwiki-cli doc delete --id 123
```

### 系统信息

```bash
mmwiki-cli version
mmwiki-cli status
```

## 配置

### 环境变量

| 变量名 | 说明 | 示例 |
|--------|------|------|
| `MMWIKI_URL` | 默认 MM-Wiki 服务器地址 | `http://localhost:8081` |
| `MMWIKI_USERNAME` | 默认用户名 | `admin` |
| `MMWIKI_PASSWORD` | 默认密码 | `secret` |

### 会话存储

登录后的 session 存储在：
- Linux/Mac: `~/.mmwiki-cli`
- Windows: `%USERPROFILE%\.mmwiki-cli`

## 在 Agent 中使用

### 示例：创建完整文档结构

```bash
# 1. 登录
mmwiki-cli login --url http://wiki.example.com --username admin --password secret

# 2. 创建空间
mmwiki-cli space create --name "API Documentation" --description "API docs" --level public --owner 1

# 3. 创建目录结构
mmwiki-cli doc create --space 1 --parent 0 --name "Getting Started" --type dir
mmwiki-cli doc create --space 1 --parent 1 --name "Authentication" --type page

# 4. 写入内容
cat > /tmp/auth.md << 'EOF'
# Authentication

## OAuth 2.0

Our API uses OAuth 2.0 for authentication...
EOF

mmwiki-cli doc write --id 2 --file /tmp/auth.md --comment "Initial content"
```

### 示例：批量操作

```bash
# 批量创建用户
for user in alice bob charlie; do
  mmwiki-cli user create \
    --username "$user" \
    --password "temp123" \
    --name "$user" \
    --role 3
done

# 导出所有文档
mmwiki-cli doc list --space 1 | while read line; do
  doc_id=$(echo $line | awk '{print $1}')
  mmwiki-cli doc read --id "$doc_id" --output "backup/$doc_id.md"
done
```

## 错误处理

CLI 工具返回非零退出码表示错误：

| 退出码 | 含义 |
|--------|------|
| `0` | 成功 |
| `1` | 一般错误 |
| `2` | 认证失败/未登录 |
| `3` | API 请求失败 |

## 注意事项

1. **API 权限**：CLI 执行的操作受限于登录用户的权限
2. **会话有效期**：Session 通常保持 24 小时，过期后需要重新登录
3. **并发限制**：大量操作时请控制并发，避免对服务器造成压力
4. **内容编码**：文档内容使用 UTF-8 编码

## API 端点映射

CLI 命令映射到以下 MM-Wiki API 端点：

| CLI 命令 | HTTP 方法 | 端点 |
|----------|-----------|------|
| `login` | POST | `/author/login` |
| `logout` | GET | `/author/logout` |
| `user list` | POST | `/system/user/lists` |
| `user get` | POST | `/system/user/detail` |
| `user create` | POST | `/system/user/save` |
| `user update` | POST | `/system/user/modify` |
| `user delete` | POST | `/system/user/delete` |
| `space list` | POST | `/system/space/lists` |
| `space get` | POST | `/system/space/detail` |
| `space create` | POST | `/system/space/save` |
| `space update` | POST | `/system/space/modify` |
| `space delete` | POST | `/system/space/delete` |
| `doc list` | POST | `/document/lists` |
| `doc create` | POST | `/document/save` |
| `doc update` | POST | `/document/modify` |
| `doc delete` | POST | `/document/delete` |
| `doc move` | POST | `/document/move` |
| `doc read` | POST | `/page/edit` |
| `doc write` | POST | `/page/save` |
