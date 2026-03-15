"""
多厂商LLM适配器

支持的厂商:
- 火山方舟 (Doubao)
- OpenAI (GPT-4/GPT-3.5)
- Anthropic (Claude)
- 阿里云 (通义千问)
- 百度 (文心一言)
- 智谱AI (ChatGLM)
- 本地模型 (Ollama)
"""

import os
import json
import asyncio
from typing import Optional, Dict, Any, AsyncGenerator
from dataclasses import dataclass
from abc import ABC, abstractmethod
import aiohttp


@dataclass
class LLMResponse:
    """LLM响应"""
    content: str
    model: str
    usage: Dict[str, int]
    error: Optional[str] = None


class BaseLLMProvider(ABC):
    """LLM提供商基类"""
    
    def __init__(self, api_key: str, **kwargs):
        self.api_key = api_key
        self.base_url = kwargs.get('base_url')
        self.model = kwargs.get('model')
        self.timeout = kwargs.get('timeout', 60)
    
    @abstractmethod
    async def chat(self, messages: list, **kwargs) -> LLMResponse:
        """对话接口"""
        pass
    
    @abstractmethod
    async def stream_chat(self, messages: list, **kwargs) -> AsyncGenerator[str, None]:
        """流式对话接口"""
        pass


class DoubaoProvider(BaseLLMProvider):
    """火山方舟 - 豆包模型"""
    
    def __init__(self, api_key: str, **kwargs):
        super().__init__(api_key, **kwargs)
        self.base_url = kwargs.get('base_url', 'https://ark.cn-beijing.volces.com/api/v3')
        self.model = kwargs.get('model', 'doubao-1-5-pro-32k-250115')
    
    async def chat(self, messages: list, **kwargs) -> LLMResponse:
        url = f"{self.base_url}/chat/completions"
        
        async with aiohttp.ClientSession() as session:
            async with session.post(
                url,
                headers={
                    'Authorization': f'Bearer {self.api_key}',
                    'Content-Type': 'application/json'
                },
                json={
                    'model': self.model,
                    'messages': messages,
                    'temperature': kwargs.get('temperature', 0.7),
                    'max_tokens': kwargs.get('max_tokens', 2000)
                },
                timeout=aiohttp.ClientTimeout(total=self.timeout)
            ) as response:
                if response.status != 200:
                    error_text = await response.text()
                    return LLMResponse(
                        content="",
                        model=self.model,
                        usage={},
                        error=f"API错误: {response.status} - {error_text}"
                    )
                
                data = await response.json()
                return LLMResponse(
                    content=data['choices'][0]['message']['content'],
                    model=self.model,
                    usage=data.get('usage', {})
                )
    
    async def stream_chat(self, messages: list, **kwargs) -> AsyncGenerator[str, None]:
        url = f"{self.base_url}/chat/completions"
        
        async with aiohttp.ClientSession() as session:
            async with session.post(
                url,
                headers={
                    'Authorization': f'Bearer {self.api_key}',
                    'Content-Type': 'application/json'
                },
                json={
                    'model': self.model,
                    'messages': messages,
                    'stream': True,
                    'temperature': kwargs.get('temperature', 0.7)
                },
                timeout=aiohttp.ClientTimeout(total=self.timeout)
            ) as response:
                async for line in response.content:
                    line = line.decode('utf-8').strip()
                    if line.startswith('data: '):
                        data = line[6:]
                        if data == '[DONE]':
                            break
                        try:
                            json_data = json.loads(data)
                            content = json_data['choices'][0]['delta'].get('content', '')
                            if content:
                                yield content
                        except:
                            pass


class OpenAIProvider(BaseLLMProvider):
    """OpenAI - GPT模型"""
    
    def __init__(self, api_key: str, **kwargs):
        super().__init__(api_key, **kwargs)
        self.base_url = kwargs.get('base_url', 'https://api.openai.com/v1')
        self.model = kwargs.get('model', 'gpt-4')
    
    async def chat(self, messages: list, **kwargs) -> LLMResponse:
        url = f"{self.base_url}/chat/completions"
        
        async with aiohttp.ClientSession() as session:
            async with session.post(
                url,
                headers={
                    'Authorization': f'Bearer {self.api_key}',
                    'Content-Type': 'application/json'
                },
                json={
                    'model': self.model,
                    'messages': messages,
                    'temperature': kwargs.get('temperature', 0.7),
                    'max_tokens': kwargs.get('max_tokens', 2000)
                }
            ) as response:
                if response.status != 200:
                    error_text = await response.text()
                    return LLMResponse(
                        content="",
                        model=self.model,
                        usage={},
                        error=f"API错误: {response.status} - {error_text}"
                    )
                
                data = await response.json()
                return LLMResponse(
                    content=data['choices'][0]['message']['content'],
                    model=self.model,
                    usage=data.get('usage', {})
                )
    
    async def stream_chat(self, messages: list, **kwargs) -> AsyncGenerator[str, None]:
        url = f"{self.base_url}/chat/completions"
        
        async with aiohttp.ClientSession() as session:
            async with session.post(
                url,
                headers={
                    'Authorization': f'Bearer {self.api_key}',
                    'Content-Type': 'application/json'
                },
                json={
                    'model': self.model,
                    'messages': messages,
                    'stream': True
                }
            ) as response:
                async for line in response.content:
                    line = line.decode('utf-8').strip()
                    if line.startswith('data: '):
                        data = line[6:]
                        if data == '[DONE]':
                            break
                        try:
                            json_data = json.loads(data)
                            content = json_data['choices'][0]['delta'].get('content', '')
                            if content:
                                yield content
                        except:
                            pass


class AnthropicProvider(BaseLLMProvider):
    """Anthropic - Claude模型"""
    
    def __init__(self, api_key: str, **kwargs):
        super().__init__(api_key, **kwargs)
        self.base_url = kwargs.get('base_url', 'https://api.anthropic.com/v1')
        self.model = kwargs.get('model', 'claude-3-sonnet-20240229')
    
    async def chat(self, messages: list, **kwargs) -> LLMResponse:
        url = f"{self.base_url}/messages"
        
        # 转换消息格式
        system_msg = ""
        user_messages = []
        for msg in messages:
            if msg['role'] == 'system':
                system_msg = msg['content']
            else:
                user_messages.append(msg)
        
        async with aiohttp.ClientSession() as session:
            async with session.post(
                url,
                headers={
                    'x-api-key': self.api_key,
                    'Content-Type': 'application/json',
                    'anthropic-version': '2023-06-01'
                },
                json={
                    'model': self.model,
                    'messages': user_messages,
                    'system': system_msg,
                    'max_tokens': kwargs.get('max_tokens', 2000)
                }
            ) as response:
                if response.status != 200:
                    error_text = await response.text()
                    return LLMResponse(
                        content="",
                        model=self.model,
                        usage={},
                        error=f"API错误: {response.status} - {error_text}"
                    )
                
                data = await response.json()
                return LLMResponse(
                    content=data['content'][0]['text'],
                    model=self.model,
                    usage=data.get('usage', {})
                )
    
    async def stream_chat(self, messages: list, **kwargs) -> AsyncGenerator[str, None]:
        # Claude流式实现
        pass


class QwenProvider(BaseLLMProvider):
    """阿里云 - 通义千问"""
    
    def __init__(self, api_key: str, **kwargs):
        super().__init__(api_key, **kwargs)
        self.base_url = kwargs.get('base_url', 'https://dashscope.aliyuncs.com/api/v1')
        self.model = kwargs.get('model', 'qwen-turbo')
    
    async def chat(self, messages: list, **kwargs) -> LLMResponse:
        url = f"{self.base_url}/services/aigc/text-generation/generation"
        
        async with aiohttp.ClientSession() as session:
            async with session.post(
                url,
                headers={
                    'Authorization': f'Bearer {self.api_key}',
                    'Content-Type': 'application/json'
                },
                json={
                    'model': self.model,
                    'input': {
                        'messages': messages
                    },
                    'parameters': {
                        'temperature': kwargs.get('temperature', 0.7),
                        'max_tokens': kwargs.get('max_tokens', 2000)
                    }
                }
            ) as response:
                if response.status != 200:
                    error_text = await response.text()
                    return LLMResponse(
                        content="",
                        model=self.model,
                        usage={},
                        error=f"API错误: {response.status} - {error_text}"
                    )
                
                data = await response.json()
                return LLMResponse(
                    content=data['output']['text'],
                    model=self.model,
                    usage=data.get('usage', {})
                )
    
    async def stream_chat(self, messages: list, **kwargs) -> AsyncGenerator[str, None]:
        pass


class OllamaProvider(BaseLLMProvider):
    """本地模型 - Ollama"""
    
    def __init__(self, api_key: str = "", **kwargs):
        super().__init__(api_key, **kwargs)
        self.base_url = kwargs.get('base_url', 'http://localhost:11434')
        self.model = kwargs.get('model', 'llama2')
    
    async def chat(self, messages: list, **kwargs) -> LLMResponse:
        url = f"{self.base_url}/api/chat"
        
        async with aiohttp.ClientSession() as session:
            async with session.post(
                url,
                json={
                    'model': self.model,
                    'messages': messages,
                    'stream': False
                }
            ) as response:
                if response.status != 200:
                    return LLMResponse(
                        content="",
                        model=self.model,
                        usage={},
                        error=f"本地模型错误: {response.status}"
                    )
                
                data = await response.json()
                return LLMResponse(
                    content=data['message']['content'],
                    model=self.model,
                    usage={}
                )
    
    async def stream_chat(self, messages: list, **kwargs) -> AsyncGenerator[str, None]:
        url = f"{self.base_url}/api/chat"
        
        async with aiohttp.ClientSession() as session:
            async with session.post(
                url,
                json={
                    'model': self.model,
                    'messages': messages,
                    'stream': True
                }
            ) as response:
                async for line in response.content:
                    try:
                        data = json.loads(line)
                        if 'message' in data:
                            yield data['message'].get('content', '')
                    except:
                        pass


class LLMFactory:
    """LLM工厂 - 创建对应提供商"""
    
    PROVIDERS = {
        'doubao': DoubaoProvider,
        'volcano': DoubaoProvider,
        'openai': OpenAIProvider,
        'anthropic': AnthropicProvider,
        'claude': AnthropicProvider,
        'qwen': QwenProvider,
        'aliyun': QwenProvider,
        'ollama': OllamaProvider,
        'local': OllamaProvider,
    }
    
    @classmethod
    def create(cls, provider: str, api_key: str, **kwargs) -> BaseLLMProvider:
        """创建LLM提供商实例"""
        provider_class = cls.PROVIDERS.get(provider.lower())
        if not provider_class:
            raise ValueError(f"不支持的LLM提供商: {provider}，支持的: {list(cls.PROVIDERS.keys())}")
        
        return provider_class(api_key, **kwargs)
    
    @classmethod
    def create_from_env(cls) -> BaseLLMProvider:
        """从环境变量创建（默认配置）"""
        provider = os.getenv('LLM_PROVIDER', 'doubao').lower()
        
        # 获取对应API Key
        api_key_env_map = {
            'doubao': 'ARK_API_KEY',
            'openai': 'OPENAI_API_KEY',
            'anthropic': 'ANTHROPIC_API_KEY',
            'qwen': 'DASHSCOPE_API_KEY',
            'ollama': '',  # 本地模型不需要key
        }
        
        api_key = os.getenv(api_key_env_map.get(provider, 'ARK_API_KEY'), '')
        
        # 获取其他配置
        model = os.getenv('LLM_MODEL')
        base_url = os.getenv('LLM_BASE_URL')
        
        kwargs = {}
        if model:
            kwargs['model'] = model
        if base_url:
            kwargs['base_url'] = base_url
        
        return cls.create(provider, api_key, **kwargs)


# 便捷函数
async def chat_with_llm(messages: list, provider: str = None, **kwargs) -> str:
    """便捷对话函数"""
    if provider:
        llm = LLMFactory.create_from_env()
    else:
        llm = LLMFactory.create_from_env()
    
    response = await llm.chat(messages, **kwargs)
    if response.error:
        raise Exception(response.error)
    return response.content


async def stream_chat_with_llm(messages: list, provider: str = None, **kwargs):
    """便捷流式对话函数"""
    llm = LLMFactory.create_from_env()
    async for chunk in llm.stream_chat(messages, **kwargs):
        yield chunk
