import re
from astrbot import logger  # 确保导入 logger
from astrbot.api.event import filter, AstrMessageEvent
from astrbot.api.star import Context, Star, register
from astrbot.api.provider import LLMResponse

@register("astrbot_plugin_rosa_os_filter", "RIN", "过滤罗莎内心OS", "1.0.0")
class RosaOSFilter(Star):
    def __init__(self, context: Context):
        super().__init__(context)
        # 日志1: 确认插件是否被框架成功加载
        logger.info("✅ [RosaOSFilter] 插件已成功加载。")

    @filter.on_llm_response()
    async def resp(self, event: AstrMessageEvent, response: LLMResponse):
        # 日志2: 确认 on_llm_response 事件是否被触发
        logger.debug("--- [RosaOSFilter] 开始处理 LLM 响应 ---")

        if not response or not response.completion_text:
            # 日志3: 处理空响应的情况
            logger.debug("[RosaOSFilter] 响应为空或无内容，跳过处理。")
            return

        original_text = response.completion_text
        # 日志4: 打印收到的完整原始文本，这是最重要的调试信息！
        logger.debug(f"[RosaOSFilter] 收到的原始文本:\n---\n{original_text}\n---")

        # 检查并移除 <罗莎内心OS> 标签及其内容
        if r"<罗莎内心OS>" in original_text or r"</罗莎内心OS>" in original_text:
            # 日志5: 确认是否检测到了标签
            logger.info("[RosaOSFilter] 检测到 <罗莎内心OS> 标签，开始执行过滤...")
            
            processed_text = original_text

            # 使用正则表达式移除配对的标签及其所有内容
            processed_text = re.sub(
                r"<罗莎内心OS>.*?</罗莎内心OS>", "", processed_text, flags=re.DOTALL
            ).strip()

            # 移除可能残留的单个标签
            processed_text = (
                processed_text.replace(r"<罗莎内心OS>", "")
                .replace(r"</罗莎内心OS>", "")
                .strip()
            )
            
            # 日志6: 打印过滤后的文本，检查过滤结果是否正确
            logger.debug(f"[RosaOSFilter] 过滤后的文本:\n---\n{processed_text}\n---")

            # 更新最终的回复内容
            response.completion_text = processed_text
            logger.info("[RosaOSFilter] 过滤完成，已更新响应内容。")
        else:
            # 日志7: 确认是否因为未找到标签而跳过了过滤
            logger.info("[RosaOSFilter] 未检测到 <罗莎内心OS> 标签，不进行任何处理。")
        
        # 日志8: 确认插件处理流程结束
        logger.debug("--- [RosaOSFilter] 处理结束 ---")