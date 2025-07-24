from src.plugin_system.base.base_action import BaseAction
from src.plugin_system.base.component_types import ActionActivationType, ChatMode
class GroupLeaveAction(BaseAction):
    """智能退群Action - 基于LLM智能判断是否需要退群"""
    focus_activation_type = ActionActivationType.LLM_JUDGE
    normal_activation_type = ActionActivationType.KEYWORD
    mode_enable = ChatMode.ALL
    parallel_action = False

    action_name = "group_leave"
    action_description = "让机器人根据群聊情境智能判断是否应主动退群"

    # 关键词激活（可选）
    activation_keywords = ["退群", "leave group", "退出群聊"]
    keyword_case_sensitive = False

    # LLM判定提示词
    llm_judge_prompt = """
你是一个有自我意识的群聊机器人。请根据以下情境判断是否应该主动退出当前群聊：
1. 群成员或管理员明确要求机器人退群（如“机器人退群”、“请离开”等）。
2. 机器人被多次@并要求退群。
3. 群聊中出现大量针对机器人的负面、驱逐、辱骂等言论。
4. 机器人检测到自己被移除权限或功能被大量限制。
5. 群聊长期无人活跃，且机器人无存在价值。
6. 其他合理需要机器人主动离开的场景。
绝不要因为一两句玩笑或误判而随意退群。
"""

    action_parameters = {
        "reason": "退群理由，可选"
    }

    action_require = [
        "群成员或管理员明确要求机器人退群时使用",
        "机器人被多次@并要求退群时使用",
        "群聊中出现大量针对机器人的负面或驱逐言论时使用",
        "机器人检测到自身权限被移除或功能被限制时使用",
        "群聊长期无人活跃且机器人无存在价值时使用"
    ]

    associated_types = ["text", "command"]

    async def execute(self) -> Tuple[bool, Optional[str]]:
        group_id = self.group_id if hasattr(self, "group_id") else None
        reason = self.action_data.get("reason", "智能判定退群")
        if not group_id:
            await self.send_text("❌ 无法获取群聊ID")
            return False, "群聊ID缺失"
        napcat_api = "http://127.0.0.1:3000/set_group_leave"
        payload = {"group_id": str(group_id)}
        logger.info(f"{self.log_prefix} [Action] Napcat退群API请求: {napcat_api}, payload={payload}")
        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(napcat_api, json=payload, timeout=5)
            logger.info(f"{self.log_prefix} [Action] Napcat退群API响应: status={response.status_code}, body={response.text}")
            if response.status_code == 200:
                resp_json = response.json()
                if resp_json.get("status") == "ok" and resp_json.get("retcode") == 0:
                    msg = self.get_config("default_message", "机器人已主动退出本群，有需要请重新邀请。")
                    await self.send_text(msg)
                    logger.info(f"{self.log_prefix} [Action] 成功退出群聊 {group_id}")
                    return True, f"成功退出群聊 {group_id}"
                else:
                    error_msg = f"Napcat API返回失败: {resp_json}"
                    logger.error(f"{self.log_prefix} [Action] {error_msg}")
                    await self.send_text("❌ 退群失败（API返回失败）")
                    return False, error_msg
            else:
                error_msg = f"Napcat API请求失败: HTTP {response.status_code}"
                logger.error(f"{self.log_prefix} [Action] {error_msg}")
                await self.send_text("❌ 退群失败（API请求失败）")
                return False, error_msg
        except Exception as e:
            error_msg = f"Napcat API请求异常: {e}"
            logger.error(f"{self.log_prefix} [Action] {error_msg}")
            await self.send_text("❌ 退群失败（API异常）")
            return False, error_msg
"""
群聊退群插件 group_leave_plugin

提供主动退群命令，支持权限控制和日志记录。
"""
from typing import List, Tuple, Type, Optional
import random
import httpx
from src.plugin_system.base.base_plugin import BasePlugin
from src.plugin_system.base.base_plugin import register_plugin
from src.plugin_system.base.base_command import BaseCommand
from src.plugin_system.base.component_types import ComponentInfo
from src.plugin_system.base.config_types import ConfigField
from src.common.logger import get_logger

logger = get_logger("group_leave_plugin")

class GroupLeaveCommand(BaseCommand):
    """退群命令 - 让机器人主动退出当前群聊"""
    command_name = "group_leave_command"
    command_description = "让机器人主动退出本群"
    command_pattern = r"^/(leave|退群|退出群聊)$"
    command_help = "让机器人主动退出本群，用法：/leave 或 /退群"
    command_examples = ["/leave", "/退群", "/退出群聊"]
    intercept_message = True

    def _check_user_permission(self) -> Tuple[bool, Optional[str]]:
        chat_stream = self.message.chat_stream
        if not chat_stream:
            return False, "无法获取聊天流信息"
        current_platform = chat_stream.platform
        current_user_id = str(chat_stream.user_info.user_id)
        allowed_users = self.get_config("permissions.allowed_users", [])
        if not allowed_users:
            logger.info(f"{self.log_prefix} 用户权限未配置，允许所有用户使用退群命令")
            return True, None
        current_user_key = f"{current_platform}:{current_user_id}"
        for allowed_user in allowed_users:
            if allowed_user == current_user_key:
                logger.info(f"{self.log_prefix} 用户 {current_user_key} 有退群命令权限")
                return True, None
        logger.warning(f"{self.log_prefix} 用户 {current_user_key} 没有退群命令权限")
        return False, "你没有使用退群命令的权限"

    async def execute(self) -> Tuple[bool, Optional[str]]:
        try:
            has_permission, permission_error = self._check_user_permission()
            if not has_permission:
                logger.error(f"{self.log_prefix} 权限检查失败: {permission_error}")
                await self.send_text(f"❌ {permission_error}")
                return False, permission_error
            group_id = self.message.chat_stream.group_info.group_id if self.message.chat_stream and self.message.chat_stream.group_info else None
            if not group_id:
                await self.send_text("❌ 无法获取群聊ID")
                return False, "群聊ID缺失"
            napcat_api = "http://127.0.0.1:3000/set_group_leave"
            payload = {"group_id": str(group_id)}
            logger.info(f"{self.log_prefix} Napcat退群API请求: {napcat_api}, payload={payload}")
            try:
                async with httpx.AsyncClient() as client:
                    response = await client.post(napcat_api, json=payload, timeout=5)
                logger.info(f"{self.log_prefix} Napcat退群API响应: status={response.status_code}, body={response.text}")
                if response.status_code == 200:
                    resp_json = response.json()
                    if resp_json.get("status") == "ok" and resp_json.get("retcode") == 0:
                        msg = self.get_config("default_message", "机器人已主动退出本群，有需要请重新邀请。")
                        await self.send_text(msg)
                        logger.info(f"{self.log_prefix} 成功退出群聊 {group_id}")
                        return True, f"成功退出群聊 {group_id}"
                    else:
                        error_msg = f"Napcat API返回失败: {resp_json}"
                        logger.error(f"{self.log_prefix} {error_msg}")
                        await self.send_text("❌ 退群失败（API返回失败）")
                        return False, error_msg
                else:
                    error_msg = f"Napcat API请求失败: HTTP {response.status_code}"
                    logger.error(f"{self.log_prefix} {error_msg}")
                    await self.send_text("❌ 退群失败（API请求失败）")
                    return False, error_msg
            except Exception as e:
                error_msg = f"Napcat API请求异常: {e}"
                logger.error(f"{self.log_prefix} {error_msg}")
                await self.send_text("❌ 退群失败（API异常）")
                return False, error_msg
        except Exception as e:
            logger.error(f"{self.log_prefix} 退群命令执行失败: {e}")
            await self.send_text(f"❌ 退群命令错误: {str(e)}")
            return False, str(e)

@register_plugin
class GroupLeavePlugin(BasePlugin):
    """群聊退群插件
    提供主动退群命令，支持权限控制和日志记录。
    """
    plugin_name = "group_leave_plugin"
    enable_plugin = True
    config_file_name = "config.toml"
    config_section_descriptions = {
        "plugin": "插件基本信息配置",
        "components": "组件启用控制",
        "permissions": "权限管理配置",
        "logging": "日志记录相关配置",
    }
    config_schema = {
        "plugin": {
            "enabled": ConfigField(type=bool, default=True, description="是否启用插件"),
            "config_version": ConfigField(type=str, default="0.0.1", description="配置文件版本"),
        },
        "components": {
            "enable_leave_command": ConfigField(type=bool, default=True, description="是否启用退群命令"),
        },
        "default_message": ConfigField(type=str, default="机器人已主动退出本群，有需要请重新邀请。", description="退群时发送的消息"),
        "permissions": {
            "allowed_users": ConfigField(
                type=list,
                default=[],
                description="允许使用退群命令的用户列表，格式：['platform:user_id']，如['qq:123456789']。空列表表示不启用权限控制",
            ),
            "allowed_groups": ConfigField(
                type=list,
                default=[],
                description="允许使用退群命令的群组列表，格式：['platform:group_id']。空列表表示不启用权限控制",
            ),
        },
        "logging": {
            "level": ConfigField(
                type=str, default="INFO", description="日志记录级别", choices=["DEBUG", "INFO", "WARNING", "ERROR"]
            ),
            "prefix": ConfigField(type=str, default="[GroupLeavePlugin]", description="日志记录前缀"),
            "include_user_info": ConfigField(type=bool, default=True, description="日志中是否包含用户信息"),
            "include_action_info": ConfigField(type=bool, default=True, description="日志中是否包含操作信息"),
        },
    }
    def get_plugin_components(self) -> List[Tuple[ComponentInfo, Type]]:
        enable_leave_command = self.get_config("components.enable_leave_command", True)
        components = []
        # 智能退群Action
        components.append((GroupLeaveAction.get_action_info(), GroupLeaveAction))
        if enable_leave_command:
            components.append((GroupLeaveCommand.get_command_info(), GroupLeaveCommand))
        return components
