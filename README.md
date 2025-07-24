# group_leave_plugin 群聊退群插件

## 插件简介

`group_leave_plugin` 是一个用于 QQ 群聊的机器人退群插件，支持通过命令让机器人主动退出当前群聊。插件支持权限控制、日志记录和自定义退群提示消息。

## 功能特性

- **退群命令 Command**：支持 `/leave`、`/退群`、`/退出群聊` 命令，机器人会主动退出当前群聊。
- **权限控制**：可配置允许使用退群命令的用户。
- **自定义消息**：退群时可自定义提示消息。
- **日志记录**：详细记录操作日志，便于追踪。

## 配置说明

插件配置文件为 `config.toml`，支持以下主要配置项：

- `plugin.enabled`：是否启用插件
- `components.enable_leave_command`：启用退群命令
- `permissions.allowed_users`：允许使用命令的用户列表
- `default_message`：退群时发送的消息
- `logging.level`：日志级别

详细配置请参考插件目录下的 `config.toml` 文件。

## 使用方法

### 1. 命令退群
- 管理员或有权限的用户可在群聊中输入：
  ```
  /leave
  /退群
  /退出群聊
  ```
- 插件会自动调用 Napcat API 让机器人退出当前群聊。

## 技术细节

- 退群操作通过 Napcat HTTP API `http://127.0.0.1:3000/set_group_leave` 实现，参数为 `group_id`。
- 插件基于麦麦插件系统开发，支持热插拔和灵活扩展。

## 目录结构

```
group_leave_plugin/
├── config.toml      # 插件配置文件
├── plugin.py        # 插件主程序
└── README.md        # 插件说明文档
```

## 联系与反馈

如有问题或建议，欢迎在项目仓库提交 issue 或联系开发者。
