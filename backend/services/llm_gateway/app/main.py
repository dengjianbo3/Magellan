# backend/services/llm_gateway/app/main.py
"""
LLM Gateway Service - 支持多 LLM 提供商
当前支持: Gemini (Google), Kimi (Moonshot AI) 和 DeepSeek
"""
import os
import io
import asyncio
from fastapi import FastAPI, HTTPException, UploadFile, File, Form, Query
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from typing import List, Optional, Literal

from .core.config import settings

# --- Pydantic Models ---
class ChatMessage(BaseModel):
    role: str
    parts: List[str]

class GenerateRequest(BaseModel):
    history: List[ChatMessage]
    # Gemini 特定参数
    thinking_level: Optional[Literal["low", "high"]] = None
    # Temperature 参数 - 控制输出随机性
    temperature: Optional[float] = None
    # 指定 LLM 提供商 (可选，默认使用系统配置)
    provider: Optional[Literal["gemini", "kimi", "deepseek"]] = None

class GenerateResponse(BaseModel):
    content: str

class ProviderInfo(BaseModel):
    name: str
    available: bool
    model: str

class ProvidersResponse(BaseModel):
    current_provider: str
    providers: List[ProviderInfo]

# --- FastAPI App ---
app = FastAPI(
    title="LLM Gateway Service (Multi-Provider)",
    description="统一的 LLM 网关服务，支持 Gemini 和 Kimi 多提供商切换",
    version="5.0.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# --- 全局客户端 ---
gemini_client = None
kimi_client = None
deepseek_client = None
current_provider = settings.DEFAULT_LLM_PROVIDER

@app.on_event("startup")
def startup_event():
    global gemini_client, kimi_client, deepseek_client, current_provider

    # 初始化 Gemini 客户端
    if settings.GOOGLE_API_KEY:
        try:
            from google import genai
            gemini_client = genai.Client(api_key=settings.GOOGLE_API_KEY)
            print(f"[LLM Gateway] Gemini client initialized (model: {settings.GEMINI_MODEL_NAME})")
        except Exception as e:
            print(f"[LLM Gateway] Failed to initialize Gemini client: {e}")

    # 初始化 Kimi 客户端 (使用 OpenAI 兼容接口)
    if settings.KIMI_API_KEY:
        try:
            from openai import OpenAI
            kimi_client = OpenAI(
                api_key=settings.KIMI_API_KEY,
                base_url=settings.KIMI_BASE_URL
            )
            print(f"[LLM Gateway] Kimi client initialized (model: {settings.KIMI_MODEL_NAME})")
        except Exception as e:
            print(f"[LLM Gateway] Failed to initialize Kimi client: {e}")

    # 初始化 DeepSeek 客户端 (使用 OpenAI 兼容接口)
    if settings.DEEPSEEK_API_KEY:
        try:
            from openai import OpenAI
            deepseek_client = OpenAI(
                api_key=settings.DEEPSEEK_API_KEY,
                base_url=settings.DEEPSEEK_BASE_URL
            )
            print(f"[LLM Gateway] DeepSeek client initialized (model: {settings.DEEPSEEK_MODEL_NAME})")
        except Exception as e:
            print(f"[LLM Gateway] Failed to initialize DeepSeek client: {e}")

    # 确定默认提供商
    if current_provider == "gemini" and not gemini_client:
        if deepseek_client:
            current_provider = "deepseek"
            print("[LLM Gateway] Gemini not available, falling back to DeepSeek")
        elif kimi_client:
            current_provider = "kimi"
            print("[LLM Gateway] Gemini not available, falling back to Kimi")
    elif current_provider == "kimi" and not kimi_client:
        if deepseek_client:
            current_provider = "deepseek"
            print("[LLM Gateway] Kimi not available, falling back to DeepSeek")
        elif gemini_client:
            current_provider = "gemini"
            print("[LLM Gateway] Kimi not available, falling back to Gemini")
    elif current_provider == "deepseek" and not deepseek_client:
        if gemini_client:
            current_provider = "gemini"
            print("[LLM Gateway] DeepSeek not available, falling back to Gemini")
        elif kimi_client:
            current_provider = "kimi"
            print("[LLM Gateway] DeepSeek not available, falling back to Kimi")

    print(f"[LLM Gateway] Current provider: {current_provider}")

# --- Gemini 调用 ---
async def call_gemini(request: GenerateRequest) -> str:
    """调用 Gemini API"""
    from google import genai
    from google.genai import types

    if not gemini_client:
        raise HTTPException(status_code=503, detail="Gemini client is not available")

    max_retries = 5
    retry_delay = 3

    for attempt in range(max_retries):
        try:
            # 转换消息格式
            contents = []
            for msg in request.history:
                contents.append(
                    types.Content(
                        role=msg.role,
                        parts=[types.Part(text=part) for part in msg.parts]
                    )
                )

            # 构建配置
            config_dict = {}
            if request.thinking_level:
                config_dict["thinking_config"] = types.ThinkingConfig(
                    thinking_level=request.thinking_level
                )
            if request.temperature is not None:
                config_dict["temperature"] = request.temperature
                print(f"[Gemini] Using temperature: {request.temperature}")

            config = types.GenerateContentConfig(**config_dict) if config_dict else None

            response = gemini_client.models.generate_content(
                model=settings.GEMINI_MODEL_NAME,
                contents=contents,
                config=config
            )

            # Ensure we return a string
            text = response.text

            # Check if text is None or empty
            if not text:
                print(f"[Gemini] Response text is empty or None: '{text}'")

                # Try to extract from parts
                if hasattr(response, 'candidates') and response.candidates:
                    try:
                        candidate = response.candidates[0]
                        # Check finish reason
                        if hasattr(candidate, 'finish_reason'):
                            print(f"[Gemini] Finish reason: {candidate.finish_reason}")
                        if hasattr(candidate, 'content') and candidate.content:
                            parts = candidate.content.parts
                            text = "".join(part.text for part in parts if hasattr(part, 'text'))
                            print(f"[Gemini] Extracted from parts: {len(text)} chars")
                    except Exception as e:
                        print(f"[Gemini] Failed to extract from parts: {e}")

                # Check for safety ratings / block reason
                if hasattr(response, 'prompt_feedback'):
                    print(f"[Gemini] Prompt feedback: {response.prompt_feedback}")

                if not text:
                    print(f"[Gemini] WARNING: Empty response. Candidates: {response.candidates if hasattr(response, 'candidates') else 'N/A'}")
                    text = "[Response blocked or empty]"

            return str(text)

        except Exception as e:
            from google.genai.errors import ServerError

            is_503_error = (isinstance(e, ServerError) and hasattr(e, 'status_code') and e.status_code == 503)

            if is_503_error and attempt < max_retries - 1:
                print(f"[Gemini] Attempt {attempt + 1}/{max_retries} failed with 503. Retrying in {retry_delay}s...")
                await asyncio.sleep(retry_delay)
                retry_delay *= 2
                continue

            print(f"[Gemini] Error: {e}")
            raise HTTPException(status_code=500, detail=f"Gemini error: {str(e)}")

# --- Kimi 调用 ---
async def call_kimi(request: GenerateRequest) -> str:
    """调用 Kimi API (OpenAI 兼容格式)"""
    if not kimi_client:
        raise HTTPException(status_code=503, detail="Kimi client is not available")

    max_retries = 3
    retry_delay = 2

    for attempt in range(max_retries):
        try:
            # 转换消息格式为 OpenAI 格式
            messages = []
            for msg in request.history:
                # Kimi 使用 content 而不是 parts
                content = "\n".join(msg.parts) if msg.parts else ""
                # 映射 role: model -> assistant
                role = "assistant" if msg.role == "model" else msg.role
                messages.append({
                    "role": role,
                    "content": content
                })

            # Kimi K2 推荐 temperature=0.6
            temperature = request.temperature if request.temperature is not None else 0.6

            print(f"[Kimi] Using temperature: {temperature}")

            # 使用同步调用（在异步上下文中）
            import asyncio
            loop = asyncio.get_event_loop()
            response = await loop.run_in_executor(
                None,
                lambda: kimi_client.chat.completions.create(
                    model=settings.KIMI_MODEL_NAME,
                    messages=messages,
                    temperature=temperature,
                    stream=False
                )
            )

            return response.choices[0].message.content

        except Exception as e:
            error_str = str(e)
            # 检查是否是可重试的错误
            is_retryable = "503" in error_str or "rate" in error_str.lower() or "timeout" in error_str.lower()

            if is_retryable and attempt < max_retries - 1:
                print(f"[Kimi] Attempt {attempt + 1}/{max_retries} failed. Retrying in {retry_delay}s...")
                await asyncio.sleep(retry_delay)
                retry_delay *= 2
                continue

            print(f"[Kimi] Error: {e}")
            raise HTTPException(status_code=500, detail=f"Kimi error: {str(e)}")

# --- DeepSeek 调用 ---
async def call_deepseek(request: GenerateRequest) -> str:
    """调用 DeepSeek API (OpenAI 兼容格式)"""
    if not deepseek_client:
        raise HTTPException(status_code=503, detail="DeepSeek client is not available")

    max_retries = 3
    retry_delay = 2

    for attempt in range(max_retries):
        try:
            # 转换消息格式为 OpenAI 格式
            messages = []
            for msg in request.history:
                # DeepSeek 使用 content 而不是 parts
                content = "\n".join(msg.parts) if msg.parts else ""
                # 映射 role: model -> assistant
                role = "assistant" if msg.role == "model" else msg.role
                messages.append({
                    "role": role,
                    "content": content
                })

            # DeepSeek 推荐 temperature=1.0 (范围 0-2)
            temperature = request.temperature if request.temperature is not None else 1.0

            print(f"[DeepSeek] Using temperature: {temperature}, model: {settings.DEEPSEEK_MODEL_NAME}")

            # 使用同步调用（在异步上下文中）
            import asyncio
            loop = asyncio.get_event_loop()
            response = await loop.run_in_executor(
                None,
                lambda: deepseek_client.chat.completions.create(
                    model=settings.DEEPSEEK_MODEL_NAME,
                    messages=messages,
                    temperature=temperature,
                    stream=False
                )
            )

            return response.choices[0].message.content

        except Exception as e:
            error_str = str(e)
            # 检查是否是可重试的错误
            is_retryable = "503" in error_str or "rate" in error_str.lower() or "timeout" in error_str.lower() or "overloaded" in error_str.lower()

            if is_retryable and attempt < max_retries - 1:
                print(f"[DeepSeek] Attempt {attempt + 1}/{max_retries} failed. Retrying in {retry_delay}s...")
                await asyncio.sleep(retry_delay)
                retry_delay *= 2
                continue

            print(f"[DeepSeek] Error: {e}")
            raise HTTPException(status_code=500, detail=f"DeepSeek error: {str(e)}")

# --- API Endpoints ---

@app.get("/providers", response_model=ProvidersResponse, tags=["Configuration"])
async def get_providers():
    """获取可用的 LLM 提供商列表和当前选择"""
    providers = [
        ProviderInfo(
            name="gemini",
            available=gemini_client is not None,
            model=settings.GEMINI_MODEL_NAME
        ),
        ProviderInfo(
            name="kimi",
            available=kimi_client is not None,
            model=settings.KIMI_MODEL_NAME
        ),
        ProviderInfo(
            name="deepseek",
            available=deepseek_client is not None,
            model=settings.DEEPSEEK_MODEL_NAME
        )
    ]
    return ProvidersResponse(
        current_provider=current_provider,
        providers=providers
    )

@app.post("/providers/{provider_name}", tags=["Configuration"])
async def set_provider(provider_name: Literal["gemini", "kimi", "deepseek"]):
    """切换当前 LLM 提供商"""
    global current_provider

    if provider_name == "gemini" and not gemini_client:
        raise HTTPException(status_code=400, detail="Gemini is not configured. Please set GOOGLE_API_KEY in .env")
    if provider_name == "kimi" and not kimi_client:
        raise HTTPException(status_code=400, detail="Kimi is not configured. Please set KIMI_API_KEY in .env")
    if provider_name == "deepseek" and not deepseek_client:
        raise HTTPException(status_code=400, detail="DeepSeek is not configured. Please set DEEPSEEK_API_KEY in .env")

    current_provider = provider_name
    print(f"[LLM Gateway] Provider switched to: {current_provider}")

    return {"message": f"Provider switched to {provider_name}", "current_provider": current_provider}

@app.post("/chat", response_model=GenerateResponse, tags=["AI Generation"])
async def chat_handler(request: GenerateRequest):
    """
    处理聊天请求，根据当前提供商路由到对应的 LLM

    - 可以通过 request.provider 临时指定提供商
    - 否则使用全局 current_provider
    """
    # 确定使用哪个提供商
    provider = request.provider or current_provider

    print(f"[LLM Gateway] Chat request using provider: {provider}")

    if provider == "gemini":
        content = await call_gemini(request)
    elif provider == "kimi":
        content = await call_kimi(request)
    elif provider == "deepseek":
        content = await call_deepseek(request)
    else:
        raise HTTPException(status_code=400, detail=f"Unknown provider: {provider}")

    return GenerateResponse(content=content)

@app.post("/generate_from_file", response_model=GenerateResponse, tags=["AI Generation"])
async def generate_from_file(
    prompt: str = Form(...),
    file: UploadFile = File(...)
):
    """
    文件理解功能 (仅 Gemini 支持)

    上传文件并使用 Gemini 进行理解和分析
    """
    from google import genai
    from google.genai import types

    if not gemini_client:
        raise HTTPException(status_code=503, detail="Gemini client is not available. File understanding requires Gemini.")

    try:
        import time

        # 1. 读取文件内容
        file_content = await file.read()
        file_io = io.BytesIO(file_content)
        file_io.name = file.filename

        # 2. 上传文件到 Files API
        upload_response = gemini_client.files.upload(
            file=file_io,
            config=types.UploadFileConfig(
                mime_type=file.content_type,
                display_name=file.filename
            )
        )

        # 3. 等待文件处理完成
        print(f"[Gemini] Uploaded file: {upload_response.name}, state: {upload_response.state}")
        while upload_response.state == "PROCESSING":
            time.sleep(1)
            upload_response = gemini_client.files.get(name=upload_response.name)
            print(f"[Gemini] File state: {upload_response.state}")

        if upload_response.state != "ACTIVE":
            raise HTTPException(status_code=500, detail=f"File processing failed with state: {upload_response.state}")

        # 4. 生成内容
        response = gemini_client.models.generate_content(
            model=settings.GEMINI_MODEL_NAME,
            contents=[
                types.Part(text=prompt),
                types.Part(file_data=types.FileData(file_uri=upload_response.uri))
            ]
        )

        # 5. 清理文件
        gemini_client.files.delete(name=upload_response.name)

        return GenerateResponse(content=response.text)

    except Exception as e:
        import traceback
        print("====== DETAILED ERROR IN llm_gateway ======")
        traceback.print_exc()
        print("============================================")
        raise HTTPException(status_code=500, detail=f"Error during generation: {str(e)}")

@app.get("/", tags=["Health Check"])
def read_root():
    return {"status": "ok", "service": "LLM Gateway", "version": "5.0.0"}

@app.get("/health", tags=["Health Check"])
def health_check():
    return {
        "status": "healthy",
        "current_provider": current_provider,
        "gemini_available": gemini_client is not None,
        "kimi_available": kimi_client is not None,
        "deepseek_available": deepseek_client is not None,
        "gemini_model": settings.GEMINI_MODEL_NAME,
        "kimi_model": settings.KIMI_MODEL_NAME,
        "deepseek_model": settings.DEEPSEEK_MODEL_NAME
    }
