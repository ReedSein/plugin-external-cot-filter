import os
import re
from datetime import datetime

from astrbot import logger
from astrbot.api.event import filter, AstrMessageEvent
from astrbot.api.star import Context, Star, register
# 关键导入：我们需要 LLMResponse 类型来直接修改模型回复
from astrbot.api.provider import LLMResponse

# --- 日志记录部分 (与原代码相同) ---
# 注意：建议将 LOG_DIR 配置化，而不是硬编码
LOG_DIR = r"logs"

def log_thought(content: str):
    """将思考内容写入独立的日志文件"""
    if not content:
        return
    try:
        if not os.path.exists(LOG_DIR):
            os.makedirs(LOG_DIR)
        now = datetime.now()
        log_file = os.path.join(LOG_DIR, f"{now.strftime('%Y-%m-%d')}_thought.log")
        with open(log_file, "a", encoding="utf-8") as f:
            f.write(f"[{now.strftime('%Y-%m-%d %H:%M:%S')}] {content}\n\n") # 增加换行以分隔日志
    except Exception as e:
        logger.error(f"写入思考日志时发生错误: {e}")

# --- 插件核心代码 (修改后) ---

@register("astrbot_plugin_external_cot_filter", "RIN", "过滤或显示外部思维链", "2.0.0")
class ExternalCoTFilter(Star):
    """
    一个用于处理外部思维链（CoT）的插件。
    它直接在LLM响应层进行操作，可以配置为：
    1. 过滤并记录思维链，仅显示最终回复。
    2. 将思维链与最终回复一起格式化显示。
    """

    # 策略1：基于最终回复标记的正则表达式进行分割 (高优先级)
    FINAL_REPLY_PATTERN = re.compile(r"最终的罗莎回复[:：]?\s*", re.IGNORECASE)

    # 策略2：基于XML标签进行过滤 (当策略1失败时使用)
    THOUGHT_TAG_PATTERN = re.compile(
        r'<(?P<tag>think|thinking|disclaimer|罗莎内心OS)>(?P<content>.*?)</(?P=tag)>',
        re.DOTALL | re.IGNORECASE
    )
    # 策略3：基于无标签的 "Thinking:" 关键词进行过滤
    UNBOUND_THINKING_PATTERN = re.compile(r'Thinking:\s*.*', re.DOTALL | re.IGNORECASE)

    def __init__(self, context: Context):
        super().__init__(context)
        # 从配置中读取是否显示思考过程，默认为False (即过滤掉)
        self.display_cot_text = (
            self.context.get_config()
            .get("provider_settings", {})
            .get("display_cot_text", False)
        )
        logger.info(f"外部思维链插件加载，显示模式: {'开启' if self.display_cot_text else '关闭'}")
        
        
    FILTERED_KEYWORDS = [
        "哦？","呵呵",
        # 以后可在此添加更多词
    ]

    @staticmethod
    def filter_keywords(text: str) -> str:
        """过滤掉指定关键词"""
        for kw in ExternalCoTFilter.FILTERED_KEYWORDS:
            text = text.replace(kw, "")
        return text


    @filter.on_llm_response()
    async def process_llm_response(self, event: AstrMessageEvent, response: LLMResponse):
        # 如果没有回复内容，则直接返回
        if not response or not response.completion_text:
            return

        original_text = response.completion_text
        thought_part = ""
        reply_part = ""

        # --- 策略1：尝试使用 "最终的蒙多回复" 标记进行分割 ---
        parts = self.FINAL_REPLY_PATTERN.split(original_text, 1)
        if len(parts) > 1:
            thought_part = parts[0].strip()
            reply_part = parts[1].strip()
            logger.debug(f"Thought: {thought_part}")
        else:
            # --- 策略2 & 3：如果策略1失败，则回退到标签和关键词过滤 ---
            
            # 先收集所有思考内容
            thoughts_found = []
            temp_text = original_text

            # 匹配带标签的思考
            for match in self.THOUGHT_TAG_PATTERN.finditer(temp_text):
                thoughts_found.append(match.group('content').strip())
            
            # 匹配无标签的 "Thinking:"
            for match in self.UNBOUND_THINKING_PATTERN.finditer(temp_text):
                # 避免重复记录已在标签内的 "Thinking:"
                if not self.THOUGHT_TAG_PATTERN.search(match.group(0)):
                    thoughts_found.append(match.group(0).strip())

            if thoughts_found:
                thought_part = "\n".join(thoughts_found)
                
                # 从原文中移除所有思考部分，得到纯净的回复
                cleaned_text = self.THOUGHT_TAG_PATTERN.sub("", original_text)
                cleaned_text = self.UNBOUND_THINKING_PATTERN.sub("", cleaned_text)
                reply_part = cleaned_text.strip()
                
                logger.debug(f"通过标签/关键词分离出思考内容: {thought_part}")
            else:
                # 如果没有任何思考标记，则认为全部都是回复内容
                reply_part = original_text.strip()

        # --- 日志记录与最终文本组装 ---

        # 无论是否显示，都记录思考过程
        if thought_part:
            log_thought(thought_part)
            
        # 关键词过滤（仅对最终回复部分处理）
        reply_part = self.filter_keywords(reply_part)

        # 根据配置决定最终输出
        if self.display_cot_text and thought_part:
            # 格式化显示思考过程和最终回复
            response.completion_text = f"🤔 思考过程：\n{thought_part}\n\n---\n\n{reply_part}"
        else:
            # 仅显示最终回复
            response.completion_text = reply_part