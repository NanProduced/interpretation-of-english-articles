# 邀请奖励功能测试操作指南

## 一、功能概述

邀请奖励功能允许已登录用户通过分享小程序给好友，当好友通过分享链接首次注册登录时，邀请者将获得 **300 永久积分（bonus_points）** 奖励。

### 核心规则

| 规则项 | 说明 |
|--------|------|
| 奖励额度 | 每成功邀请 1 人 = 300 积分 |
| 奖励上限 | 最多可邀请 10 人（最多获得 3000 积分） |
| 奖励对象 | **仅奖励邀请者**，被邀请者暂无奖励 |
| 防自邀 | 同一用户不能邀请自己 |
| 防重复 | 一个新用户只能归属一个邀请者（首次进入时的 inviter_id 为准） |
| 奖励类型 | 永久积分（bonus_points），不清零，可累积使用 |

---

## 二、前置准备

### 1. 执行数据库迁移

在服务器端执行新的数据库迁移文件：

```bash
# 进入 server 目录
cd server

# 连接 PostgreSQL 数据库并执行迁移
# 方式一：使用 psql 命令行
psql -h localhost -U postgres -d your_database_name -f db/migrations/0005_invite_reward_system.sql

# 方式二：使用数据库管理工具（如 DBeaver、pgAdmin）
# 打开 db/migrations/0005_invite_reward_system.sql，复制内容执行
```

### 2. 验证迁移是否成功

执行以下 SQL 查询验证表是否创建：

```sql
-- 检查新表是否存在
SELECT table_name FROM information_schema.tables WHERE table_name = 'user_invites';

-- 检查 users 表是否有新字段
SELECT column_name FROM information_schema.columns 
WHERE table_name = 'users' AND column_name IN ('inviter_id', 'successful_invite_count');
```

### 3. 启动后端服务

确保后端服务已启动并监听正确的端口：

```bash
cd server
# 使用 uvicorn 或其他方式启动
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

---

## 三、微信开发者工具中模拟测试（单人单机）

### 测试场景说明

在微信开发者工具中，我们可以通过以下方式模拟完整的邀请闭环：

1. **邀请者用户（User A）**：已登录用户，分享带参链接
2. **被邀请者用户（User B）**：新用户，通过带参链接进入并首次登录

由于微信开发者工具在同一台电脑上只能模拟一个用户，我们需要通过**手动模拟参数**和**清理本地存储**来模拟两个不同的用户。

---

### 测试步骤详解

#### 阶段一：准备邀请者（User A）

**目标**：获取一个已登录用户的 user_id，作为 inviter_id。

1. **打开微信开发者工具**，导入小程序项目

2. **确保已登录用户状态**：
   - 点击底部导航「我的」
   - 如果显示「点击登录微信」，点击进行登录
   - 登录成功后，用户信息会显示在页面顶部

3. **获取当前用户的 user_id**：

   方式一：通过控制台日志
   - 打开开发者工具的「调试器」→「Console」
   - 在 Console 中输入以下代码获取用户信息：
   ```javascript
   // 获取当前登录用户信息
   const userInfo = Taro.getStorageSync('auth_user_info')
   console.log('当前用户信息:', JSON.parse(userInfo))
   console.log('user_id:', JSON.parse(userInfo).user_id)
   ```
   
   方式二：通过 Network 面板
   - 切换到「Network」面板
   - 点击「我的」页面触发刷新
   - 找到请求 `/auth/session/me`
   - 查看 Response 中的 `user_id` 字段

4. **记录 user_id**：
   - 将获取到的 user_id 复制保存，例如：
   ```
   user_id = "550e8400-e29b-41d4-a716-446655440000"
   ```

---

#### 阶段二：模拟被邀请者（User B）点击带参链接

**目标**：模拟新用户通过带有 inviter 参数的分享链接进入小程序。

1. **清理当前用户状态**（模拟新用户）：

   在 Console 中执行以下代码清除本地存储：
   ```javascript
   // 清除所有相关的本地存储
   Taro.removeStorageSync('auth_token')
   Taro.removeStorageSync('auth_user_info')
   Taro.removeStorageSync('user_configured')
   Taro.removeStorageSync('guest_dismissed')
   Taro.removeStorageSync('pending_inviter_id')
   
   // 验证是否清除成功
   console.log('auth_token:', Taro.getStorageSync('auth_token'))
   console.log('auth_user_info:', Taro.getStorageSync('auth_user_info'))
   ```

   > 注意：此时页面应该显示「点击登录微信」的未登录状态。

2. **模拟带参进入小程序**：

   方式一：通过 Taro.showLaunchOptionsSync 模拟（推荐）

   在 Console 中执行：
   ```javascript
   // 替换 YOUR_INVITER_USER_ID 为阶段一中获取的 user_id
   const inviterId = "YOUR_INVITER_USER_ID"  // 例如："550e8400-e29b-41d4-a716-446655440000"
   
   // 手动缓存 inviter_id（模拟 App.onLaunch 捕获参数）
   Taro.setStorageSync('pending_inviter_id', inviterId)
   
   console.log('已设置邀请者ID:', Taro.getStorageSync('pending_inviter_id'))
   ```

   方式二：通过编译模式（更贴近真实场景）

   1. 点击微信开发者工具顶部的「普通编译」下拉菜单
   2. 选择「添加编译模式」
   3. 填写以下信息：
      - 模式名称：`邀请链接测试`
      - 启动页面：`pages/home/index`（或任意首页）
      - 启动参数：`inviter=YOUR_INVITER_USER_ID`（替换为实际的 user_id）
      - 进入场景：选择 `1007`（单人聊天会话中的小程序消息卡片）或 `1008`（群聊会话中的小程序消息卡片）
   4. 点击「确定」保存
   5. 重新编译小程序，此时会自动带有 inviter 参数

   > 验证方式：在 Console 中查看 `[app] Launch options:` 日志，确认 query 中包含 inviter 参数。

---

#### 阶段三：被邀请者首次登录

**目标**：模拟新用户首次登录，触发邀请奖励发放。

1. **触发登录**：
   - 点击「我的」页面
   - 点击「点击登录微信」或「微信登录」按钮
   - 微信开发者工具会模拟微信登录流程

2. **观察登录结果**：

   成功场景（奖励发放）：
   - 应该看到 Toast 提示：`获得 300 积分奖励！`
   - 或者普通的 `登录成功` 提示

   失败场景（不发放奖励）：
   - 如果邀请者 ID 无效或被邀请者不是新用户，会显示普通的 `登录成功`
   - 可以在 Network 面板查看 `/auth/wechat/login` 的响应

3. **验证登录 API 响应**：

   在 Network 面板中：
   - 找到请求 `POST /auth/wechat/login`
   - 查看 Response：

   **成功发放奖励时的响应示例**：
   ```json
   {
     "user_id": "new-user-uuid-here",
     "session_token": "session-token-here",
     "expires_at": "2026-05-17T12:34:56Z",
     "invite_reward_applied": true,
     "invite_reward_points": 300
   }
   ```

   **未发放奖励时的响应示例**：
   ```json
   {
     "user_id": "existing-user-uuid-here",
     "session_token": "session-token-here",
     "expires_at": "2026-05-17T12:34:56Z",
     "invite_reward_applied": false,
     "invite_reward_reason": "already_has_inviter"
   }
   ```

---

#### 阶段四：验证奖励是否到账

**目标**：验证邀请者的积分是否增加，以及邀请计数是否更新。

##### 4.1 前端验证

1. **重新登录为邀请者（User A）**：

   先清除当前登录状态（模拟切换回邀请者）：
   ```javascript
   // 清除当前登录状态
   Taro.removeStorageSync('auth_token')
   Taro.removeStorageSync('auth_user_info')
   Taro.removeStorageSync('user_configured')
   ```

   然后重新登录（邀请者账号）。

2. **查看「我的」页面**：

   - 检查「永久奖励积分」是否增加了 300
   - 检查「邀请好友」菜单项是否显示 `已邀请 1/10 人`

3. **通过 Console 验证**：

   ```javascript
   // 查看用户信息中的邀请计数
   const userInfo = JSON.parse(Taro.getStorageSync('auth_user_info'))
   console.log('成功邀请人数:', userInfo.successfulInviteCount)
   ```

##### 4.2 数据库验证（更准确）

连接数据库执行以下查询：

```sql
-- 1. 查看邀请关系表
SELECT * FROM user_invites;

-- 预期结果：应有一条记录
-- inviter_id = 邀请者的 user_id
-- invitee_id = 被邀请者的 user_id
-- reward_applied = true
-- reward_points = 300

-- 2. 查看邀请者的成功邀请计数
SELECT id, display_name, successful_invite_count 
FROM users 
WHERE id = '邀请者的user_id';

-- 预期结果：successful_invite_count = 1

-- 3. 查看邀请者的积分账户
SELECT user_id, bonus_points, daily_free_points, daily_used_points
FROM user_credit_accounts
WHERE user_id = '邀请者的user_id';

-- 预期结果：bonus_points 应该比之前增加了 300

-- 4. 查看积分流水
SELECT * FROM user_credit_ledger 
WHERE user_id = '邀请者的user_id'
ORDER BY created_at DESC 
LIMIT 5;

-- 预期结果：应有一条 entry_type = 'bonus_grant' 的记录
-- points = 300
-- bucket_type = 'bonus'
```

---

## 四、边界条件测试

### 测试用例 1：自邀测试（自己邀请自己）

**目标**：验证用户不能邀请自己。

**步骤**：
1. 记录当前用户的 user_id（设为 UUID_A）
2. 清除登录状态
3. 设置 inviter_id = UUID_A（自己邀请自己）
4. 重新登录
5. 验证奖励未发放

**预期结果**：
- `/auth/wechat/login` 响应中 `invite_reward_applied = false`
- `invite_reward_reason = "self_invite"`
- 邀请者积分无变化
- `user_invites` 表无新增记录

---

### 测试用例 2：重复邀请测试（同一被邀请者多次登录）

**目标**：验证一个新用户只能获得一次邀请奖励。

**步骤**：
1. 用 inviter_id = UUID_A 首次登录（User B）→ 应该发放奖励
2. 退出登录（清除 token，但保留 inviter_id 缓存）
3. 再次登录（User B 已有账号）
4. 验证第二次登录不发放奖励

**预期结果**：
- 第二次登录时 `invite_reward_applied = false`
- `invite_reward_reason = "already_has_inviter"`（因为 users.inviter_id 已设置）
- 只有第一条邀请记录
- 邀请者的 successful_invite_count 仍为 1

---

### 测试用例 3：邀请者达到上限（邀请 10 人后）

**目标**：验证邀请者达到 10 人上限后不再发放奖励。

**步骤**：
1. 在数据库中手动设置邀请者的 successful_invite_count = 10：
   ```sql
   UPDATE users SET successful_invite_count = 10 WHERE id = 'UUID_A';
   ```
2. 模拟新用户（User C）使用 inviter_id = UUID_A 登录
3. 验证奖励未发放

**预期结果**：
- `invite_reward_applied = false`
- `invite_reward_reason = "max_invite_count_reached"`
- 无积分增加

---

### 测试用例 4：无效的邀请者 ID

**目标**：验证 inviter_id 格式错误或不存在时不报错。

**步骤**：
1. 清除登录状态
2. 设置无效的 inviter_id：
   ```javascript
   Taro.setStorageSync('pending_inviter_id', 'not-a-valid-uuid')
   ```
3. 登录新用户
4. 验证登录成功但无奖励

**预期结果**：
- 登录成功（不因为 inviter_id 无效而阻塞登录）
- `invite_reward_applied = false`
- `invite_reward_reason = "invalid_inviter_id"` 或 `"inviter_not_found"`

---

### 测试用例 5：无 inviter_id 的正常登录

**目标**：验证普通登录流程不受影响。

**步骤**：
1. 清除登录状态和 inviter_id 缓存
2. 正常登录新用户
3. 验证登录成功

**预期结果**：
- 登录成功
- `invite_reward_applied = false`（因为没有 inviter_id）
- 无 invite_reward_reason 字段

---

## 五、排查问题指南

### 常见问题 1：邀请参数未被捕获

**症状**：被邀请者登录后没有获得奖励，Network 中也没有 inviter_id 参数。

**排查步骤**：
1. 检查 App.onLaunch 是否正确执行：
   - 在 Console 中查看是否有 `[app] Launch options:` 日志
   - 检查日志中的 query 是否包含 inviter

2. 验证本地存储是否正确：
   ```javascript
   console.log('pending_inviter_id:', Taro.getStorageSync('pending_inviter_id'))
   ```

3. 检查是否在登录前被错误清除：
   - 确保没有其他代码在登录前调用 `Taro.removeStorageSync('pending_inviter_id')`

---

### 常见问题 2：奖励未发放但没有错误日志

**症状**：被邀请者是新用户，inviter_id 正确，但没有发放奖励。

**排查步骤**：
1. 检查后端日志，查看是否有：
   - `New user login with inviter:` 日志
   - `Invite reward applied:` 或 `Invite reward not applied:` 日志

2. 检查数据库中的用户状态：
   ```sql
   -- 检查被邀请者是否真的是新用户
   SELECT id, created_at, inviter_id FROM users WHERE id = '被邀请者ID';
   
   -- 检查邀请关系表
   SELECT * FROM user_invites WHERE invitee_id = '被邀请者ID';
   ```

3. 可能的原因：
   - 被邀请者之前已经登录过（users 表中已存在记录）
   - 被邀请者的 inviter_id 已被设置（之前被其他人邀请过）
   - 邀请者的 successful_invite_count 已达到 10

---

### 常见问题 3：数据库迁移失败

**症状**：执行迁移 SQL 时报错。

**排查步骤**：
1. 检查 PostgreSQL 版本（需要支持 UUID 和 JSONB）
2. 检查是否已存在同名的表或字段
3. 分步执行 SQL 定位问题：
   ```sql
   -- 先检查表是否存在
   SELECT * FROM user_invites LIMIT 1;
   
   -- 如果不存在，单独执行创建表语句
   CREATE TABLE user_invites (
       id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
       -- ... 其他字段
   );
   ```

---

## 六、关键代码位置速查

| 功能模块 | 文件路径 | 关键函数/方法 |
|---------|---------|--------------|
| **前端-参数捕获** | `client/src/app.tsx` | `extractInviterId()`, `savePendingInviter()` |
| **前端-登录传参** | `client/src/services/auth.ts` | `ensureLoggedIn()`, `getPendingInviterId()` |
| **前端-API调用** | `client/src/services/api/client.ts` | `fetchWeChatLogin()` |
| **前端-分享功能** | `client/src/pages/profile/index.tsx` | `useShareAppMessage()` |
| **后端-登录路由** | `server/app/api/routes/auth.py` | `wechat_login()` |
| **后端-邀请奖励** | `server/app/services/auth/invite_reward.py` | `apply_invite_reward()` |
| **后端-用户创建** | `server/app/services/auth/session.py` | `get_or_create_user_by_wechat()` |
| **数据库迁移** | `server/db/migrations/0005_invite_reward_system.sql` | - |

---

## 七、测试清单

在完成功能开发后，请确保以下测试用例全部通过：

| # | 测试项 | 预期结果 | 状态 |
|---|--------|---------|------|
| 1 | 邀请者分享链接带有正确的 inviter 参数 | path 中包含 `?inviter=user_id` | ⬜ |
| 2 | 被邀请者通过带参链接进入能捕获 inviter_id | `pending_inviter_id` 被正确缓存 | ⬜ |
| 3 | 新用户首次登录时 inviter_id 被传递到后端 | `/auth/wechat/login` 请求包含 inviter_id | ⬜ |
| 4 | 邀请奖励正确发放 | 邀请者 bonus_points += 300 | ⬜ |
| 5 | 邀请关系正确记录 | `user_invites` 表有记录 | ⬜ |
| 6 | 邀请计数正确更新 | `users.successful_invite_count += 1` | ⬜ |
| 7 | 积分流水正确记录 | `user_credit_ledger` 有 bonus_grant 记录 | ⬜ |
| 8 | 自邀被拒绝 | 无奖励，reason= self_invite | ⬜ |
| 9 | 重复邀请被拒绝 | 无奖励，reason= already_has_inviter | ⬜ |
| 10 | 达到上限后拒绝 | 无奖励，reason= max_invite_count_reached | ⬜ |
| 11 | 无效邀请者 ID 不阻塞登录 | 登录成功，无奖励 | ⬜ |
| 12 | 无 inviter_id 的正常登录不受影响 | 登录成功 | ⬜ |
| 13 | 前端正确显示邀请计数 | 「我的」页面显示已邀请人数 | ⬜ |

---

## 八、回滚方案

如果需要回滚邀请奖励功能，可以执行以下操作：

### 数据库回滚

```sql
-- 1. 删除 user_invites 表
DROP TABLE IF EXISTS user_invites;

-- 2. 删除 users 表的新增字段
ALTER TABLE users DROP COLUMN IF EXISTS inviter_id;
ALTER TABLE users DROP COLUMN IF EXISTS successful_invite_count;

-- 3. 删除相关的积分流水（可选）
-- DELETE FROM user_credit_ledger WHERE entry_type = 'bonus_grant' AND metadata_json::text LIKE '%invite_reward%';
```

### 代码回滚

1. 恢复 `server/app/services/auth/session.py` 中的 `get_or_create_user_by_wechat` 函数签名
2. 恢复 `server/app/api/routes/auth.py` 中的 `wechat_login` 函数
3. 删除 `server/app/services/auth/invite_reward.py` 文件
4. 恢复前端相关修改

---

**文档版本**：v1.0  
**最后更新**：2026-04-17  
**对应代码版本**：邀请奖励功能首次实现
