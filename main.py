# -*- coding: utf-8 -*-

"""
astrbot_plugin_rosa_cot_filter.py

为角色“罗莎 (Rosa)”定制的思维链（Chain of Thought, CoT）处理插件。
此插件旨在将罗莎的“内心独白”（模型的思考过程）与她最终的“言语”（对用户的回复）进行精确分离，
以确保最终输出的文本完全符合其深刻、复杂且高度一致的人格设定。

版本: 1.0.0
适配角色: 罗莎 (Rosa)
"""

import os
import re
from datetime import datetime

# 关键的 astrbot 框架导入
from astrbot import logger
from astrbot.api.event import filter, AstrMessageEvent
from astrbot.api.star import Context, Star, register
from astrbot.api.provider import LLMResponse

# --- 日志记录模块 ---
# 用于将模型的“内心独白”记录到本地文件，以便调试和分析。
LOG_DIR = r"logs"

def log_thought(content: str):
    """将罗莎的内心独白内容写入独立的日志文件"""
    if not content:
        return
    try:
        if not os.path.exists(LOG_DIR):
            os.makedirs(LOG_DIR)
        now = datetime.now()
        log_file = os.path.join(LOG_DIR, f"{now.strftime('%Y-%m-%d')}_rosa_thought.log")
        with open(log_file, "a", encoding="utf-8") as f:
            f.write(f"[{now.strftime('%Y-%m-%d %H:%M:%S')}] --- 罗莎的内心独白 ---\n{content}\n\n")
    except Exception as e:
        logger.error(f"写入罗莎思考日志时发生错误: {e}")

# --- 插件核心类 ---

@register(
    "astrbot_plugin_rosa_cot_filter",
    "罗莎思维链过滤器",
    "过滤或显示罗莎的内心独白，确保人格一致性",
    "1.0.0"
)
class RosaCoTFilter(Star):
    """
    一个为角色“罗莎”定制的思维链（CoT）处理插件。
    它将罗莎的“内心独白”与最终的“言语”分离，以确保输出的绝对人格一致性。
    """

    # --- 为罗莎定制的正则表达式 ---

    # 策略1：基于优雅的最终言语标记进行分割。
    # (?:罗莎的)? 表示 "罗莎的" 这部分是可选的，增加了匹配的鲁棒性。
    FINAL_REPLY_PATTERN = re.compile(r"(?:罗莎的)?最终言语[:：]?\s*", re.IGNORECASE)

    # 策略2：基于罗莎心理活动的XML标签进行匹配。
    # 这些标签应在系统提示词中明确指示模型使用。
    THOUGHT_TAG_PATTERN = re.compile(
        r'<(?P<tag>内心独白|无声的观察|意识流动)>(?P<content>.*?)</(?P=tag)>',
        re.DOTALL | re.IGNORECASE
    )
    
    # 策略3：基于罗莎风格的无标签关键词进行匹配。
    # 作为备用方案，以防模型忘记使用XML标签。
    UNBOUND_THINKING_PATTERN = re.compile(r'思索[:：]\s*.*', re.DOTALL | re.IGNORECASE)
    
    # --- 为罗莎定制的过滤词库 ---
    # 过滤掉任何可能破坏罗莎优雅、疏离人设的犹豫填充词或粗俗词语。
    FILTERED_KEYWORDS = [
        "呃...", "那个...", "嗯...", "这个嘛...", "卧槽", "牛逼", "我操"
    ]

    def __init__(self, context: Context):
        super().__init__(context)
        # 从配置中读取是否在调试时显示思考过程，默认为False (即过滤掉)
        self.display_cot_text = (
            self.context.get_config()
            .get("provider_settings", {})
            .get("display_cot_text", False)
        )
        logger.info(f"罗莎思维链过滤器加载成功，显示模式: {'开启 (调试模式)' if self.display_cot_text else '关闭 (常规模式)'}")
        
    @staticmethod
    def filter_keywords(text: str) -> str:
        """静态方法：从文本中过滤掉所有在 FILTERED_KEYWORDS 列表中的词"""
        for kw in RosaCoTFilter.FILTERED_KEYWORDS:
            text = text.replace(kw, "")
        return text

    @filter.on_llm_response()
    async def process_llm_response(self, event: AstrMessageEvent, response: LLMResponse):
        """在每次LLM响应后执行此过滤函数"""
        if not response or not response.completion_text:
            return

        original_text = response.completion_text
        thought_part = ""
        reply_part = ""

        # --- 策略1：尝试使用 "最终言语" 标记进行分割 ---
        parts = self.FINAL_REPLY_PATTERN.split(original_text, 1)
        if len(parts) > 1:
            thought_part = parts[0].strip()
            reply_part = parts[1].strip()
            logger.debug(f"罗莎思维链 (通过'最终言语'标记分离): {thought_part}")
        else:
            # --- 策略2 & 3：如果策略1失败，则回退到标签和关键词过滤 ---
            thoughts_found = []
            
            # 先用标签匹配来收集所有思考内容
            for match in self.THOUGHT_TAG_PATTERN.finditer(original_text):
                thoughts_found.append(match.group('content').strip())
            
            # 再用无标签关键词匹配
            for match in self.UNBOUND_THINKING_PATTERN.finditer(original_text):
                # 检查以避免重复记录已在XML标签内的内容
                if not self.THOUGHT_TAG_PATTERN.search(match.group(0)):
                    thoughts_found.append(match.group(0).strip())

            if thoughts_found:
                thought_part = "\n".join(thoughts_found)
                
                # 从原文中移除所有思考部分，得到纯净的回复
                cleaned_text = self.THOUGHT_TAG_PATTERN.sub("", original_text)
                cleaned_text = self.UNBOUND_THINKING_PATTERN.sub("", cleaned_text)
                reply_part = cleaned_text.strip()
                
                logger.debug(f"罗莎思维链 (通过标签/关键词分离): {thought_part}")
            else:
                # 如果没有任何思考标记，则认为全部都是回复内容
                reply_part = original_text.strip()

        # --- 日志记录与最终文本组装 ---

        # 无论是否显示，都将思考过程记录到日志
        if thought_part:
            log_thought(thought_part)
            
        # 对最终要发出的言语部分进行关键词过滤
        reply_part = self.filter_keywords(reply_part)

        # 根据配置决定最终输出给用户的文本
        if self.display_cot_text and thought_part:
            # 调试模式：格式化显示思考过程和最终回复
            response.completion_text = f"【幕后的思绪】\n{thought_part}\n\n---\n\n{reply_part}"
        else:
            # 常规模式：仅显示纯净的、符合人设的最终回复
            response.completion_text = reply_part