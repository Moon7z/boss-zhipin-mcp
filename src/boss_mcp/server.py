from mcp.server import Server
from mcp.server.stdio import stdio_server
from mcp.types import Tool, TextContent
from mcp.server import NotificationOptions
from pydantic import AnyUrl
import asyncio
import json
from pathlib import Path

from boss_mcp.resume_parser import parse_resume
from boss_mcp.boss_client import BossZhipinClient, JobInfo, ResumeData


app = Server("boss-zhipin-mcp")

current_client: BossZhipinClient = None
current_resume = None


@app.list_tools()
async def list_tools() -> list[Tool]:
    return [
        Tool(
            name="boss_login",
            description="登录BOSS直聘账号（需要手机号和密码），支持反机器人检测",
            inputSchema={
                "type": "object",
                "properties": {
                    "phone": {"type": "string", "description": "手机号"},
                    "password": {"type": "string", "description": "密码"},
                    "headless": {"type": "boolean", "description": "是否无头模式运行浏览器", "default": False},
                    "use_proxy": {"type": "boolean", "description": "是否使用代理IP", "default": False},
                    "enable_anti_detection": {"type": "boolean", "description": "是否启用反检测功能（推荐开启）", "default": True},
                    "max_requests_per_minute": {"type": "integer", "description": "每分钟最大请求数", "default": 8}
                },
                "required": ["phone", "password"]
            }
        ),
        Tool(
            name="load_resume",
            description="解析本地简历文件（支持PDF和DOCX格式），提取关键信息",
            inputSchema={
                "type": "object",
                "properties": {
                    "resume_path": {"type": "string", "description": "简历文件路径"}
                },
                "required": ["resume_path"]
            }
        ),
        Tool(
            name="search_jobs",
            description="在BOSS直聘上搜索符合条件的岗位",
            inputSchema={
                "type": "object",
                "properties": {
                    "keyword": {"type": "string", "description": "搜索关键词，如'Python开发'"},
                    "city": {"type": "string", "description": "期望城市，如'北京'"},
                    "experience": {"type": "string", "description": "工作经验要求，如'1-3年'"},
                    "education": {"type": "string", "description": "学历要求，如'本科'"},
                    "salary": {"type": "string", "description": "薪资范围，如'20K-40K'"},
                    "page_count": {"type": "integer", "description": "搜索页数", "default": 3}
                },
                "required": ["keyword"]
            }
        ),
        Tool(
            name="match_and_greet",
            description="根据简历信息匹配岗位并自动打招呼（需要先登录和加载简历）",
            inputSchema={
                "type": "object",
                "properties": {
                    "keyword": {"type": "string", "description": "搜索关键词"},
                    "min_score": {"type": "integer", "description": "最低匹配分数阈值(0-100)", "default": 30},
                    "max_count": {"type": "integer", "description": "最多打招呼的岗位数量", "default": 10},
                    "custom_message": {"type": "string", "description": "自定义打招呼消息模板"}
                },
                "required": ["keyword"]
            }
        ),
        Tool(
            name="get_recommended_jobs",
            description="根据已加载的简历智能推荐匹配的岗位",
            inputSchema={
                "type": "object",
                "properties": {
                    "keyword": {"type": "string", "description": "搜索关键词"},
                    "min_score": {"type": "integer", "description": "最低匹配分数", "default": 50},
                    "max_count": {"type": "integer", "description": "返回的最大岗位数量", "default": 20}
                },
                "required": ["keyword"]
            }
        ),
        Tool(
            name="close_browser",
            description="关闭浏览器会话",
            inputSchema={
                "type": "object",
                "properties": {}
            }
        ),
        Tool(
            name="get_resume_info",
            description="获取当前已加载的简历信息",
            inputSchema={
                "type": "object",
                "properties": {}
            }
        )
    ]


@app.call_tool()
async def call_tool(name: str, arguments: dict) -> list[TextContent]:
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
                return [TextContent(type="text", text=json.dumps({"success": True, "message": "登录成功"}, ensure_ascii=False))]
            else:
                client.close()
                return [TextContent(type="text", text=json.dumps({"success": False, "message": "登录失败，请检查账号密码"}, ensure_ascii=False))]
        
        elif name == "load_resume":
            resume_path = arguments.get("resume_path")
            if not resume_path:
                return [TextContent(type="text", text=json.dumps({"success": False, "message": "请提供简历路径"}, ensure_ascii=False))]
            
            path = Path(resume_path)
            if not path.exists():
                return [TextContent(type="text", text=json.dumps({"success": False, "message": f"文件不存在: {resume_path}"}, ensure_ascii=False))]
            
            resume_data = parse_resume(resume_path)
            current_resume = ResumeData(
                skills=resume_data.get("skills", []),
                experience_years=resume_data.get("experience_years", 0),
                education=resume_data.get("education", ""),
                expected_position=resume_data.get("expected_position", ""),
                expected_city=resume_data.get("expected_city", ""),
                name=resume_data.get("name", "")
            )
            
            return [TextContent(type="text", text=json.dumps({"success": True, "resume": resume_data}, ensure_ascii=False, indent=2))]
        
        elif name == "search_jobs":
            if not current_client:
                return [TextContent(type="text", text=json.dumps({"success": False, "message": "请先登录BOSS直聘"}, ensure_ascii=False))]
            
            keyword = arguments.get("keyword", "")
            city = arguments.get("city", "")
            experience = arguments.get("experience", "")
            education = arguments.get("education", "")
            salary = arguments.get("salary", "")
            page_count = arguments.get("page_count", 3)
            
            jobs = current_client.search_jobs(
                keyword=keyword,
                city=city,
                experience=experience,
                education=education,
                salary=salary,
                page_count=page_count
            )
            
            jobs_data = [
                {
                    "job_id": job.job_id,
                    "title": job.title,
                    "company": job.company,
                    "salary": job.salary,
                    "city": job.city,
                    "experience": job.experience,
                    "education": job.education,
                    "description": job.description[:200] + "..." if len(job.description) > 200 else job.description,
                    "hr_name": job.hr_name,
                    "hr_active_status": job.hr_active_status
                }
                for job in jobs
            ]
            
            return [TextContent(type="text", text=json.dumps({"success": True, "jobs": jobs_data, "total": len(jobs_data)}, ensure_ascii=False, indent=2))]
        
        elif name == "match_and_greet":
            if not current_client:
                return [TextContent(type="text", text=json.dumps({"success": False, "message": "请先登录BOSS直聘"}, ensure_ascii=False))]
            
            if not current_resume:
                return [TextContent(type="text", text=json.dumps({"success": False, "message": "请先加载简历"}, ensure_ascii=False))]
            
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
            
            results = current_client.batch_greet(
                filtered_jobs,
                current_resume,
                min_score=min_score,
                custom_message_template=custom_message
            )
            
            return [TextContent(type="text", text=json.dumps({"success": True, "results": results}, ensure_ascii=False, indent=2))]
        
        elif name == "get_recommended_jobs":
            if not current_client:
                return [TextContent(type="text", text=json.dumps({"success": False, "message": "请先登录BOSS直聘"}, ensure_ascii=False))]
            
            if not current_resume:
                return [TextContent(type="text", text=json.dumps({"success": False, "message": "请先加载简历"}, ensure_ascii=False))]
            
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
                            "hr_name": job.hr_name,
                            "hr_active_status": job.hr_active_status
                        },
                        "match_score": score
                    })
            
            job_scores.sort(key=lambda x: x["match_score"], reverse=True)
            recommended = job_scores[:max_count]
            
            return [TextContent(type="text", text=json.dumps({"success": True, "recommended_jobs": recommended, "resume_info": {
                "name": current_resume.name,
                "skills": current_resume.skills,
                "experience_years": current_resume.experience_years,
                "education": current_resume.education,
                "expected_position": current_resume.expected_position,
                "expected_city": current_resume.expected_city
            }}, ensure_ascii=False, indent=2))]
        
        elif name == "close_browser":
            if current_client:
                current_client.close()
                current_client = None
            return [TextContent(type="text", text=json.dumps({"success": True, "message": "浏览器已关闭"}, ensure_ascii=False))]
        
        elif name == "get_resume_info":
            if not current_resume:
                return [TextContent(type="text", text=json.dumps({"success": False, "message": "尚未加载简历"}, ensure_ascii=False))]
            
            return [TextContent(type="text", text=json.dumps({"success": True, "resume": {
                "name": current_resume.name,
                "skills": current_resume.skills,
                "experience_years": current_resume.experience_years,
                "education": current_resume.education,
                "expected_position": current_resume.expected_position,
                "expected_city": current_resume.expected_city
            }}, ensure_ascii=False, indent=2))]
        
        else:
            return [TextContent(type="text", text=json.dumps({"success": False, "message": f"未知工具: {name}"}))]
    
    except Exception as e:
        return [TextContent(type="text", text=json.dumps({"success": False, "error": str(e)}, ensure_ascii=False))]


async def main():
    async with stdio_server() as (read_stream, write_stream):
        await app.run(
            read_stream,
            write_stream,
            app.create_initialization_options(
                notification_options=NotificationOptions(),
                server_info={
                    "name": "boss-zhipin-mcp",
                    "version": "0.1.0"
                }
            )
        )


if __name__ == "__main__":
    asyncio.run(main())
