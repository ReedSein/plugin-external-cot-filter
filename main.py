import re
from astrbot.api.event import filter, AstrMessageEvent
from astrbot.api.star import Context, Star, register
from astrbot.api.provider import LLMResponse

@register("astrbot_plugin_rosa_os_filter", "RIN", "过滤罗莎内心OS", "1.0.0")
class RosaOSFilter(Star):
    def __init__(self, context: Context):
        super().__init__(context)

    @filter.on_llm_response()
    async def resp(self, event: AstrMessageEvent, response: LLMResponse):
        # 仅在存在回复文本时执行
        if not response or not response.completion_text:
            return

        completion_text = response.completion_text

        # 检查并移除 <罗莎内心OS> 标签及其内容
        if r"<罗莎内心OS>" in completion_text or r"</罗莎内心OS>" in completion_text:
            # 使用正则表达式移除配对的标签及其所有内容
            completion_text = re.sub(
                r"<罗莎内心OS>.*?</罗莎内心OS>", "", completion_text, flags=re.DOTALL
            ).strip()

            # 移除可能残留的单个标签
            completion_text = (
                completion_text.replace(r"<罗莎内心OS>", "")
                .replace(r"</罗莎内心OS>", "")
                .strip()
            )

            # 更新最终的回复内容
            response.completion_text = completion_text