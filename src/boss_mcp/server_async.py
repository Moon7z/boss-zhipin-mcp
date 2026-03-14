"""
异步HTTP MCP服务器（高性能版本）

特性：
- FastAPI异步框架
- WebSocket实时通信
- 并发请求处理
- 健康监控
"""

import asyncio
import json
import logging
from typing import Optional, Dict, Any
from contextlib import asynccontextmanager

from fastapi import FastAPI, WebSocket, WebSocketDisconnect, HTTPException
from fastapi.responses import JSONResponse
from pydantic import BaseModel

from boss_mcp.boss_client_async import AsyncBossZhipinClient, ResumeData
from boss_mcp.resume_parser import ResumeParser

logger = logging.getLogger(__name__)

# 全局客户端实例
client: Optional[AsyncBossZhipinClient] = None
resume_data: Optional[ResumeData] = None


class LoginRequest(BaseModel):
    phone: str
    password: str
    headless: bool = True
    enable_anti_detection: bool = True


class SearchRequest(BaseModel):
    keyword: str
    city: str = ""
    page: int = 1


class MatchRequest(BaseModel):
    keyword: str
    min_score: int = 60
    max_count: int = 10


class ResumeUploadRequest(BaseModel):
    resume_path: str


@asynccontextmanager
async def lifespan(app: FastAPI):
    """应用生命周期管理"""
    global client
    
    # 启动时初始化
    logger.info("启动BOSS直聘MCP服务器...")
    client = AsyncBossZhipinClient(
        headless=True,
        enable_anti_detection=True,
        max_concurrent=3
    )
    await client.start()
    
    yield
    
    # 关闭时清理
    logger.info("关闭服务器...")
    if client:
        await client.close()


app = FastAPI(
    title="BOSS直聘MCP服务器",
    description="异步高性能版本",
    version="2.0.0",
    lifespan=lifespan
)


@app.get("/health")
async def health_check():
    """健康检查"""
    return {
        "status": "ok",
        "client_ready": client is not None and client.is_logged_in,
        "timestamp": asyncio.get_event_loop().time()
    }


@app.post("/login")
async def login(request: LoginRequest):
    """登录BOSS直聘"""
    if not client:
        raise HTTPException(status_code=503, detail="客户端未初始化")
    
    try:
        # 这里需要实现实际的登录逻辑
        # 暂时返回模拟结果
        return {
            "success": True,
            "message": "登录成功",
            "phone": request.phone[:3] + "****" + request.phone[-4:]
        }
    except Exception as e:
        logger.error(f"登录失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/login/status")
async def login_status():
    """检查登录状态"""
    if not client:
        return {"logged_in": False, "reason": "客户端未启动"}
    
    is_logged_in = await client.check_login()
    return {
        "logged_in": is_logged_in,
        "cookies_exist": client.cookies_path.exists()
    }


@app.post("/resume/upload")
async def upload_resume(request: ResumeUploadRequest):
    """上传并解析简历"""
    global resume_data
    
    try:
        parser = ResumeParser()
        resume_data = parser.parse(request.resume_path)
        
        return {
            "success": True,
            "data": {
                "name": resume_data.name,
                "skills": resume_data.skills[:10],
                "experience_years": resume_data.experience_years,
                "education": resume_data.education,
            }
        }
    except Exception as e:
        logger.error(f"解析简历失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/jobs/search")
async def search_jobs(request: SearchRequest):
    """搜索岗位"""
    if not client:
        raise HTTPException(status_code=503, detail="客户端未初始化")
    
    try:
        jobs = await client.search_jobs(
            keyword=request.keyword,
            city=request.city,
            page=request.page
        )
        
        return {
            "success": True,
            "count": len(jobs),
            "jobs": [
                {
                    "title": job.title,
                    "company": job.company,
                    "salary": job.salary,
                    "match_score": job.match_score
                }
                for job in jobs[:10]
            ]
        }
    except Exception as e:
        logger.error(f"搜索失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/jobs/match")
async def match_jobs(request: MatchRequest):
    """智能匹配岗位"""
    if not client or not resume_data:
        raise HTTPException(
            status_code=400, 
            detail="请先上传简历"
        )
    
    try:
        # 搜索岗位
        jobs = await client.search_jobs(request.keyword)
        
        # 匹配并打招呼
        results = []
        async for result in client.match_and_greet(
            jobs, 
            resume_data, 
            min_score=request.min_score
        ):
            results.append({
                "title": result["job"].title,
                "company": result["job"].company,
                "match_score": result["match_score"],
                "match_reason": result.get("match_reason", ""),
                "message": result.get("message", ""),
                "status": result["status"]
            })
            
            if len(results) >= request.max_count:
                break
        
        return {
            "success": True,
            "matched_count": len([r for r in results if r["status"] == "matched"]),
            "results": results
        }
    
    except Exception as e:
        logger.error(f"匹配失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# WebSocket支持
@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    """WebSocket实时通信"""
    await websocket.accept()
    
    try:
        while True:
            # 接收消息
            data = await websocket.receive_text()
            message = json.loads(data)
            
            action = message.get("action")
            
            if action == "search":
                # 执行搜索
                keyword = message.get("keyword", "")
                jobs = await client.search_jobs(keyword) if client else []
                
                await websocket.send_json({
                    "type": "search_result",
                    "count": len(jobs),
                    "jobs": [{"title": j.title, "company": j.company} for j in jobs[:5]]
                })
            
            elif action == "ping":
                await websocket.send_json({"type": "pong"})
            
            else:
                await websocket.send_json({
                    "type": "error",
                    "message": f"未知操作: {action}"
                })
    
    except WebSocketDisconnect:
        logger.info("WebSocket客户端断开连接")
    except Exception as e:
        logger.error(f"WebSocket错误: {e}")
        await websocket.close()


# MCP协议兼容端点
@app.post("/mcp")
async def mcp_endpoint(request: Dict[str, Any]):
    """MCP协议端点"""
    method = request.get("method")
    params = request.get("params", {})
    
    if method == "tools/list":
        return {
            "tools": [
                {
                    "name": "boss_login",
                    "description": "登录BOSS直聘",
                    "parameters": {
                        "phone": {"type": "string"},
                        "password": {"type": "string"}
                    }
                },
                {
                    "name": "search_jobs",
                    "description": "搜索岗位",
                    "parameters": {
                        "keyword": {"type": "string"},
                        "city": {"type": "string"}
                    }
                },
                {
                    "name": "match_and_greet",
                    "description": "智能匹配并打招呼",
                    "parameters": {
                        "keyword": {"type": "string"},
                        "min_score": {"type": "integer"}
                    }
                }
            ]
        }
    
    elif method == "tools/call":
        tool_name = params.get("name")
        
        if tool_name == "search_jobs":
            keyword = params.get("arguments", {}).get("keyword", "")
            jobs = await client.search_jobs(keyword) if client else []
            return {
                "content": [
                    {"type": "text", "text": f"找到{len(jobs)}个岗位"}
                ]
            }
        
        return {"error": f"未知工具: {tool_name}"}
    
    return {"error": "未知方法"}


if __name__ == "__main__":
    import uvicorn
    
    uvicorn.run(
        app,
        host="0.0.0.0",
        port=18061,
        log_level="info"
    )
