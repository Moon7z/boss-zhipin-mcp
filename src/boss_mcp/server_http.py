from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse, StreamingResponse
from pydantic import BaseModel
import asyncio
import json
import logging
from typing import Optional

from boss_mcp.resume_parser import parse_resume
from boss_mcp.boss_client import BossZhipinClient, JobInfo, ResumeData

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(title="BOSS Zhipin MCP Server", version="0.2.0")

current_client: Optional[BossZhipinClient] = None
current_resume: Optional[ResumeData] = None


class LoginRequest(BaseModel):
    phone: str
    password: str
    headless: bool = False
    use_proxy: bool = False
    enable_anti_detection: bool = True
    max_requests_per_minute: int = 8


class ResumeRequest(BaseModel):
    resume_path: str


class SearchRequest(BaseModel):
    keyword: str
    city: str = ""
    experience: str = ""
    education: str = ""
    salary: str = ""
    page_count: int = 3


class GreetRequest(BaseModel):
    keyword: str
    min_score: int = 30
    max_count: int = 10
    custom_message: str = ""


class RecommendRequest(BaseModel):
    keyword: str = ""
    min_score: int = 50
    max_count: int = 20


def make_mcp_response(result: dict):
    return JSONResponse(content=result)


@app.get("/")
async def root():
    return {"status": "ok", "service": "BOSS Zhipin MCP Server", "version": "0.2.0"}


@app.get("/health")
async def health():
    return {"status": "healthy", "logged_in": current_client.is_logged_in if current_client else False}


@app.post("/mcp")
async def mcp_endpoint(request: Request):
    global current_client, current_resume
    
    body = await request.json()
    method = body.get("method")
    params = body.get("params", {})
    
    try:
        if method == "initialize":
            return make_mcp_response({
                "jsonrpc": "2.0",
                "id": body.get("id"),
                "result": {
                    "protocolVersion": "2024-11-05",
                    "serverInfo": {
                        "name": "boss-zhipin-mcp",
                        "version": "0.2.0"
                    },
                    "capabilities": {
                        "tools": {}
                    }
                }
            })
        
        elif method == "tools/list":
            tools = [
                {"name": "boss_login", "description": "登录BOSS直聘账号", "inputSchema": {"type": "object", "properties": {"phone": {"type": "string"}, "password": {"type": "string"}, "headless": {"type": "boolean"}}}},
                {"name": "load_resume", "description": "解析简历文件", "inputSchema": {"type": "object", "properties": {"resume_path": {"type": "string"}}}},
                {"name": "search_jobs", "description": "搜索岗位", "inputSchema": {"type": "object", "properties": {"keyword": {"type": "string"}, "city": {"type": "string"}, "page_count": {"type": "integer"}}}},
                {"name": "match_and_greet", "description": "匹配岗位并打招呼", "inputSchema": {"type": "object", "properties": {"keyword": {"type": "string"}, "min_score": {"type": "integer"}, "max_count": {"type": "integer"}}}},
                {"name": "get_recommended_jobs", "description": "获取推荐岗位", "inputSchema": {"type": "object", "properties": {"keyword": {"type": "string"}, "min_score": {"type": "integer"}}}},
                {"name": "check_login_status", "description": "检查登录状态", "inputSchema": {"type": "object", "properties": {}}},
                {"name": "get_resume_info", "description": "获取简历信息", "inputSchema": {"type": "object", "properties": {}}},
                {"name": "close_browser", "description": "关闭浏览器", "inputSchema": {"type": "object", "properties": {}}}
            ]
            return make_mcp_response({
                "jsonrpc": "2.0",
                "id": body.get("id"),
                "result": {"tools": tools}
            })
        
        elif method == "tools/call":
            tool_name = params.get("name")
            arguments = params.get("arguments", {})
            
            result = await call_mcp_tool(tool_name, arguments)
            
            return make_mcp_response({
                "jsonrpc": "2.0",
                "id": body.get("id"),
                "result": {"content": [{"type": "text", "text": json.dumps(result, ensure_ascii=False)}]}
            })
        
        else:
            return make_mcp_response({
                "jsonrpc": "2.0",
                "id": body.get("id"),
                "error": {"code": -32601, "message": f"Method not found: {method}"}
            })
    
    except Exception as e:
        logger.error(f"MCP error: {e}")
        return make_mcp_response({
            "jsonrpc": "2.0",
            "id": body.get("id"),
            "error": {"code": -32603, "message": str(e)}
        })


async def call_mcp_tool(name: str, arguments: dict) -> dict:
    global current_client, current_resume
    
    try:
        if name == "boss_login":
            phone = arguments.get("phone")
            password = arguments.get("password")
            headless = arguments.get("headless", False)
            use_proxy = arguments.get("use_proxy", False)
            enable_anti_detection = arguments.get("enable_anti_detection", True)
            max_requests_per_minute = arguments.get("max_requests_per_minute", 8)
            
            client = BossZhipinClient(
                headless=headless,
                use_proxy=use_proxy,
                enable_anti_detection=enable_anti_detection,
                max_requests_per_minute=max_requests_per_minute
            )
            client.start()
            
            success = client.login(phone, password)
            
            if success:
                current_client = client
                return {"success": True, "message": "登录成功"}
            else:
                client.close()
                return {"success": False, "message": "登录失败，请检查账号密码"}
        
        elif name == "load_resume":
            resume_path = arguments.get("resume_path")
            if not resume_path:
                return {"success": False, "message": "请提供简历路径"}
            
            resume_data = parse_resume(resume_path)
            current_resume = ResumeData(
                skills=resume_data.get("skills", []),
                experience_years=resume_data.get("experience_years", 0),
                education=resume_data.get("education", ""),
                expected_position=resume_data.get("expected_position", ""),
                expected_city=resume_data.get("expected_city", ""),
                name=resume_data.get("name", "")
            )
            
            return {"success": True, "resume": resume_data}
        
        elif name == "search_jobs":
            if not current_client:
                return {"success": False, "message": "请先登录BOSS直聘"}
            
            keyword = arguments.get("keyword", "")
            city = arguments.get("city", "")
            page_count = arguments.get("page_count", 3)
            
            jobs = current_client.search_jobs(keyword=keyword, city=city, page_count=page_count)
            
            jobs_data = [
                {
                    "job_id": job.job_id,
                    "title": job.title,
                    "company": job.company,
                    "salary": job.salary,
                    "city": job.city,
                    "experience": job.experience,
                    "education": job.education,
                    "hr_name": job.hr_name,
                    "hr_active_status": job.hr_active_status
                }
                for job in jobs
            ]
            
            return {"success": True, "jobs": jobs_data, "total": len(jobs_data)}
        
        elif name == "match_and_greet":
            if not current_client:
                return {"success": False, "message": "请先登录BOSS直聘"}
            
            if not current_resume:
                return {"success": False, "message": "请先加载简历"}
            
            keyword = arguments.get("keyword", "")
            min_score = arguments.get("min_score", 30)
            max_count = arguments.get("max_count", 10)
            custom_message = arguments.get("custom_message", "")
            
            jobs = current_client.search_jobs(keyword=keyword, page_count=3)
            
            filtered_jobs = []
            for job in jobs:
                score = current_client.calculate_match_score(job, current_resume)
                if score >= min_score:
                    filtered_jobs.append(job)
                    if len(filtered_jobs) >= max_count:
                        break
            
            results = current_client.batch_greet(filtered_jobs, current_resume, min_score=min_score, custom_message_template=custom_message)
            
            return {"success": True, "results": results}
        
        elif name == "get_recommended_jobs":
            if not current_client:
                return {"success": False, "message": "请先登录BOSS直聘"}
            
            if not current_resume:
                return {"success": False, "message": "请先加载简历"}
            
            keyword = arguments.get("keyword", current_resume.expected_position or "Python开发")
            min_score = arguments.get("min_score", 50)
            max_count = arguments.get("max_count", 20)
            
            jobs = current_client.search_jobs(keyword=keyword, page_count=3)
            
            job_scores = []
            for job in jobs:
                score = current_client.calculate_match_score(job, current_resume)
                if score >= min_score:
                    job_scores.append({
                        "job": {
                            "job_id": job.job_id,
                            "title": job.title,
                            "company": job.company,
                            "salary": job.salary,
                            "city": job.city,
                            "experience": job.experience,
                            "education": job.education,
                            "hr_name": job.hr_name
                        },
                        "match_score": score
                    })
            
            job_scores.sort(key=lambda x: x["match_score"], reverse=True)
            
            return {"success": True, "recommended_jobs": job_scores[:max_count]}
        
        elif name == "check_login_status":
            if not current_client:
                return {"success": True, "logged_in": False, "message": "未启动浏览器"}
            
            is_logged_in = current_client.check_login_status()
            return {"success": True, "logged_in": is_logged_in}
        
        elif name == "get_resume_info":
            if not current_resume:
                return {"success": False, "message": "尚未加载简历"}
            
            return {
                "success": True,
                "resume": {
                    "name": current_resume.name,
                    "skills": current_resume.skills,
                    "experience_years": current_resume.experience_years,
                    "education": current_resume.education,
                    "expected_position": current_resume.expected_position,
                    "expected_city": current_resume.expected_city
                }
            }
        
        elif name == "close_browser":
            if current_client:
                current_client.close()
                current_client = None
            return {"success": True, "message": "浏览器已关闭"}
        
        else:
            return {"success": False, "message": f"未知工具: {name}"}
    
    except Exception as e:
        return {"success": False, "error": str(e)}


def main():
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=18061)


if __name__ == "__main__":
    main()
