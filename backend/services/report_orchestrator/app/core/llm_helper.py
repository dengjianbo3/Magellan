"""
LLM Helper - 通用的LLM调用封装
统一处理与LLM Gateway的交互
"""
import httpx
import json
import re
from typing import Dict, Any, List, Optional
from datetime import datetime


class LLMHelper:
    """LLM调用助手,统一封装LLM交互逻辑"""

    def __init__(
        self,
        llm_gateway_url: str = "http://llm_gateway:8003",
        timeout: int = 120
    ):
        """
        初始化LLM Helper

        Args:
            llm_gateway_url: LLM Gateway服务地址
            timeout: 请求超时时间(秒)
        """
        self.llm_gateway_url = llm_gateway_url
        self.timeout = timeout

    async def call(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        response_format: str = "json"
    ) -> Dict[str, Any]:
        """
        调用LLM并解析响应

        Args:
            prompt: 用户提示词
            system_prompt: 系统提示词(可选)
            response_format: 期望的响应格式 ("json" | "text")

        Returns:
            解析后的响应(JSON格式返回dict,text格式返回{"content": str})
        """
        # 构建请求历史
        history = []

        if system_prompt:
            history.append({
                "role": "user",
                "parts": [system_prompt]
            })

        history.append({
            "role": "user",
            "parts": [prompt]
        })

        # 调用LLM
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.post(
                    f"{self.llm_gateway_url}/chat",
                    json={"history": history}
                )

                if response.status_code != 200:
                    raise Exception(f"LLM Gateway returned {response.status_code}: {response.text}")

                result = response.json()
                content = result.get("content", "")

                # 根据响应格式解析
                if response_format == "json":
                    return self._parse_json_response(content)
                else:
                    return {"content": content}

        except httpx.TimeoutException:
            print(f"[LLMHelper] Request timeout after {self.timeout}s")
            return self._create_timeout_response()

        except Exception as e:
            print(f"[LLMHelper] Error calling LLM: {e}")
            return self._create_error_response(str(e))

    def _parse_json_response(self, content: str) -> Dict[str, Any]:
        """
        解析JSON格式的响应

        尝试多种方式提取JSON:
        1. 直接JSON解析
        2. 从Markdown代码块中提取
        3. 使用正则表达式查找JSON对象

        Args:
            content: LLM响应内容

        Returns:
            解析后的JSON对象
        """
        # 1. 直接解析
        try:
            return json.loads(content)
        except json.JSONDecodeError:
            pass

        # 2. 从Markdown代码块提取
        match = re.search(r'```json\n(.*?)\n```', content, re.DOTALL)
        if match:
            try:
                return json.loads(match.group(1))
            except json.JSONDecodeError:
                pass

        # 3. 查找第一个JSON对象
        match = re.search(r'\{.*\}', content, re.DOTALL)
        if match:
            try:
                return json.loads(match.group(0))
            except json.JSONDecodeError:
                pass

        # 4. 解析失败,返回原文本
        print(f"[LLMHelper] Failed to parse JSON, returning raw content")
        return {
            "error": "JSON parsing failed",
            "raw_content": content
        }

    def _create_timeout_response(self) -> Dict[str, Any]:
        """创建超时响应"""
        return {
            "error": "timeout",
            "message": "LLM请求超时",
            "timestamp": datetime.now().isoformat()
        }

    def _create_error_response(self, error_msg: str) -> Dict[str, Any]:
        """创建错误响应"""
        return {
            "error": "llm_error",
            "message": error_msg,
            "timestamp": datetime.now().isoformat()
        }

    async def call_with_retry(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        response_format: str = "json",
        max_retries: int = 2
    ) -> Dict[str, Any]:
        """
        带重试机制的LLM调用

        Args:
            prompt: 用户提示词
            system_prompt: 系统提示词
            response_format: 响应格式
            max_retries: 最大重试次数

        Returns:
            解析后的响应
        """
        last_error = None

        for attempt in range(max_retries + 1):
            try:
                result = await self.call(prompt, system_prompt, response_format)

                # 检查是否有错误
                if "error" not in result:
                    return result

                last_error = result

            except Exception as e:
                last_error = str(e)
                print(f"[LLMHelper] Attempt {attempt + 1} failed: {e}")

            # 如果不是最后一次尝试,等待后重试
            if attempt < max_retries:
                await self._wait_before_retry(attempt)

        # 所有重试都失败
        return {
            "error": "max_retries_exceeded",
            "message": f"Failed after {max_retries + 1} attempts",
            "last_error": last_error
        }

    async def _wait_before_retry(self, attempt: int):
        """重试前等待"""
        import asyncio
        wait_time = min(2 ** attempt, 10)  # 指数退避,最多10秒
        await asyncio.sleep(wait_time)


# 创建全局LLM Helper实例
llm_helper = LLMHelper()
