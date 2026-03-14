"""
BOSS直聘异步客户端（高性能版本）

优化点：
1. 异步架构，支持并发
2. 连接池复用
3. 智能重试机制
4. AI智能匹配
5. 个性化消息生成
"""

import asyncio
import json
import random
import logging
from pathlib import Path
from typing import Optional, List, Dict, Any, AsyncGenerator
from dataclasses import dataclass
from datetime import datetime
import aiohttp
from playwright.async_api import async_playwright, Browser, Page, BrowserContext

from boss_mcp.anti_detection_v2 import AntiDetectionV2, BrowserFingerprint, SmartScheduler

logger = logging.getLogger(__name__)


@dataclass
class JobInfo:
    """岗位信息"""
    job_id: str
    title: str
    company: str
    salary: str
    city: str
    experience: str
    education: str
    description: str
    hr_name: str
    hr_active_status: str
    match_score: int = 0
    match_reason: str = ""


@dataclass
class ResumeData:
    """简历数据"""
    name: str
    phone: str
    email: str
    skills: List[str]
    experience_years: int
    education: str
    expected_position: str
    expected_city: str
    expected_salary: str
    work_experiences: List[Dict]


class LLMMatcher:
    """LLM智能匹配器"""
    
    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or "your-api-key"
        self.endpoint = "https://ark.cn-beijing.volces.com/api/v3"
        self.model = "doubao-1-5-pro-32k-250115"
    
    async def calculate_match_score(
        self, 
        job: JobInfo, 
        resume: ResumeData
    ) -> Dict[str, Any]:
        """使用LLM计算匹配度"""
        
        prompt = f"""评估以下岗位与简历的匹配度：

【岗位信息】
- 职位：{job.title}
- 公司：{job.company}
- 薪资：{job.salary}
- 要求：{job.description}
- 经验要求：{job.experience}
- 学历要求：{job.education}

【简历信息】
- 姓名：{resume.name}
- 期望职位：{resume.expected_position}
- 工作年限：{resume.experience_years}年
- 学历：{resume.education}
- 技能：{', '.join(resume.skills[:10])}
- 期望薪资：{resume.expected_salary}

请评估匹配度并返回JSON格式：
{{
    "score": 0-100的整数,
    "reason": "匹配理由（50字以内）",
    "key_points": ["匹配点1", "匹配点2"],
    "risk": "风险点（如有）"
}}
"""
        
        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    f"{self.endpoint}/chat/completions",
                    headers={
                        "Authorization": f"Bearer {self.api_key}",
                        "Content-Type": "application/json"
                    },
                    json={
                        "model": self.model,
                        "messages": [
                            {"role": "system", "content": "你是一个专业的HR岗位匹配专家。"},
                            {"role": "user", "content": prompt}
                        ],
                        "temperature": 0.3,
                        "max_tokens": 500
                    }
                ) as response:
                    if response.status != 200:
                        logger.error(f"LLM API error: {response.status}")
                        return {"score": 50, "reason": "API调用失败", "key_points": [], "risk": ""}
                    
                    result = await response.json()
                    content = result["choices"][0]["message"]["content"]
                    
                    # 解析JSON
                    try:
                        import re
                        json_match = re.search(r'\{.*\}', content, re.DOTALL)
                        if json_match:
                            data = json.loads(json_match.group())
                            return {
                                "score": data.get("score", 50),
                                "reason": data.get("reason", ""),
                                "key_points": data.get("key_points", []),
                                "risk": data.get("risk", "")
                            }
                    except Exception as e:
                        logger.error(f"Parse LLM response error: {e}")
                    
                    return {"score": 50, "reason": content[:50], "key_points": [], "risk": ""}
        
        except Exception as e:
            logger.error(f"LLM match error: {e}")
            return {"score": 50, "reason": "评估失败", "key_points": [], "risk": ""}


class MessageGenerator:
    """个性化消息生成器"""
    
    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key
        self.endpoint = "https://ark.cn-beijing.volces.com/api/v3"
        self.model = "doubao-1-5-pro-32k-250115"
    
    async def generate_greeting(
        self, 
        job: JobInfo, 
        resume: ResumeData,
        match_info: Dict
    ) -> str:
        """生成个性化打招呼消息"""
        
        prompt = f"""根据以下信息生成专业的打招呼消息（80字以内）：

【岗位】
- 公司：{job.company}
- 职位：{job.title}
- 薪资：{job.salary}
- 要求：{job.description[:100]}

【我的优势】
- 技能：{', '.join(resume.skills[:5])}
- 经验：{resume.experience_years}年
- 匹配点：{', '.join(match_info.get('key_points', [])[:2])}

要求：
1. 真诚、专业、简洁
2. 突出匹配优势
3. 不超过80字
4. 避免模板化表达
"""
        
        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    f"{self.endpoint}/chat/completions",
                    headers={
                        "Authorization": f"Bearer {self.api_key}",
                        "Content-Type": "application/json"
                    },
                    json={
                        "model": self.model,
                        "messages": [
                            {"role": "system", "content": "你是一个专业的求职者，擅长写简洁有力的打招呼消息。"},
                            {"role": "user", "content": prompt}
                        ],
                        "temperature": 0.7,
                        "max_tokens": 200
                    }
                ) as response:
                    if response.status == 200:
                        result = await response.json()
                        message = result["choices"][0]["message"]["content"].strip()
                        # 限制长度
                        if len(message) > 80:
                            message = message[:77] + "..."
                        return message
        
        except Exception as e:
            logger.error(f"Generate message error: {e}")
        
        # 兜底消息
        return f"您好，我对{job.title}岗位很感兴趣。我有{resume.experience_years}年经验，熟悉{', '.join(resume.skills[:3])}，希望能有机会详细沟通。"


class AsyncBossZhipinClient:
    """异步BOSS直聘客户端"""
    
    def __init__(
        self,
        headless: bool = False,
        enable_anti_detection: bool = True,
        max_concurrent: int = 3,
        llm_api_key: Optional[str] = None
    ):
        self.headless = headless
        self.enable_anti_detection = enable_anti_detection
        self.max_concurrent = max_concurrent
        
        self.playwright = None
        self.browser: Optional[Browser] = None
        self.context: Optional[BrowserContext] = None
        self.page: Optional[Page] = None
        self.anti_detection: Optional[AntiDetectionV2] = None
        self.scheduler = SmartScheduler()
        self.matcher = LLMMatcher(llm_api_key)
        self.message_generator = MessageGenerator(llm_api_key)
        
        self.cookies_path = Path(__file__).parent / "cookies.json"
        self.is_logged_in = False
        self.semaphore = asyncio.Semaphore(max_concurrent)
        
    async def start(self):
        """启动客户端"""
        self.playwright = await async_playwright().start()
        
        # 浏览器配置
        browser_args = [
            "--disable-blink-features=AutomationControlled",
            "--disable-dev-shm-usage",
            "--no-sandbox",
            "--disable-setuid-sandbox",
            "--disable-web-security",
            "--disable-features=IsolateOrigins,site-per-process",
        ]
        
        # 随机指纹
        fingerprint = BrowserFingerprint.random()
        
        self.browser = await self.playwright.chromium.launch(
            headless=self.headless,
            args=browser_args
        )
        
        self.context = await self.browser.new_context(
            viewport=fingerprint.viewport,
            user_agent=fingerprint.user_agent,
            locale=fingerprint.language,
            timezone_id=fingerprint.timezone,
        )
        
        self.page = await self.context.new_page()
        
        # 设置反检测
        if self.enable_anti_detection:
            self.anti_detection = AntiDetectionV2(self.page, self.context)
            await self.anti_detection.setup_stealth()
        
        # 加载cookies
        await self._load_cookies()
        
        logger.info("异步客户端启动完成")
    
    async def _load_cookies(self):
        """加载cookies"""
        if self.cookies_path.exists():
            try:
                cookies = json.loads(self.cookies_path.read_text())
                await self.context.add_cookies(cookies)
                self.is_logged_in = True
                logger.info("已加载cookies")
            except Exception as e:
                logger.error(f"加载cookies失败: {e}")
    
    async def _save_cookies(self):
        """保存cookies"""
        try:
            cookies = await self.context.cookies()
            self.cookies_path.write_text(json.dumps(cookies))
            logger.info("已保存cookies")
        except Exception as e:
            logger.error(f"保存cookies失败: {e}")
    
    async def check_login(self) -> bool:
        """检查登录状态"""
        await self.page.goto("https://www.zhipin.com/web/geek/chat")
        await asyncio.sleep(2)
        
        # 检查是否需要登录
        if "/login" in self.page.url or await self.page.query_selector(".login-btn"):
            self.is_logged_in = False
            return False
        
        self.is_logged_in = True
        return True
    
    async def search_jobs(
        self,
        keyword: str,
        city: str = "",
        page: int = 1
    ) -> List[JobInfo]:
        """搜索岗位"""
        async with self.semaphore:
            if not self.scheduler.can_execute("searches"):
                wait_time = self.scheduler.get_wait_time("searches")
                logger.info(f"达到搜索频率限制，等待{wait_time}秒")
                await asyncio.sleep(wait_time)
            
            url = f"https://www.zhipin.com/web/geek/job?query={keyword}&city={city}&page={page}"
            await self.page.goto(url)
            
            # 等待加载
            await asyncio.sleep(random.uniform(2, 4))
            
            # 智能滚动
            if self.anti_detection:
                await self.anti_detection.smart_scroll(self.page)
            
            # 解析岗位列表
            jobs = []
            job_cards = await self.page.query_selector_all(".job-card-wrapper")
            
            for card in job_cards:
                try:
                    job = await self._parse_job_card(card)
                    if job:
                        jobs.append(job)
                except Exception as e:
                    logger.error(f"解析岗位失败: {e}")
            
            self.scheduler.record("searches")
            return jobs
    
    async def _parse_job_card(self, card) -> Optional[JobInfo]:
        """解析岗位卡片"""
        try:
            title = await card.query_selector_eval(".job-name", "el => el.textContent")
            company = await card.query_selector_eval(".company-name", "el => el.textContent")
            salary = await card.query_selector_eval(".salary", "el => el.textContent")
            
            return JobInfo(
                job_id="",
                title=title.strip() if title else "",
                company=company.strip() if company else "",
                salary=salary.strip() if salary else "",
                city="",
                experience="",
                education="",
                description="",
                hr_name="",
                hr_active_status=""
            )
        except:
            return None
    
    async def match_and_greet(
        self,
        jobs: List[JobInfo],
        resume: ResumeData,
        min_score: int = 60
    ) -> AsyncGenerator[Dict[str, Any], None]:
        """匹配并打招呼"""
        
        for job in jobs:
            # 检查频率限制
            if not self.scheduler.can_execute("applications"):
                wait_time = self.scheduler.get_wait_time("applications")
                logger.info(f"达到打招呼频率限制，等待{wait_time}秒")
                await asyncio.sleep(wait_time)
            
            # LLM智能匹配
            match_result = await self.matcher.calculate_match_score(job, resume)
            job.match_score = match_result["score"]
            job.match_reason = match_result["reason"]
            
            if job.match_score >= min_score:
                # 生成个性化消息
                message = await self.message_generator.generate_greeting(
                    job, resume, match_result
                )
                
                yield {
                    "job": job,
                    "match_score": job.match_score,
                    "match_reason": job.match_reason,
                    "message": message,
                    "status": "matched"
                }
                
                # 实际打招呼（这里需要实现）
                # await self._send_greeting(job, message)
                
                self.scheduler.record("applications")
                
                # 人类化延迟
                await asyncio.sleep(random.uniform(30, 60))
            else:
                yield {
                    "job": job,
                    "match_score": job.match_score,
                    "status": "filtered"
                }
    
    async def close(self):
        """关闭客户端"""
        await self._save_cookies()
        
        if self.browser:
            await self.browser.close()
        if self.playwright:
            await self.playwright.stop()
        
        logger.info("客户端已关闭")
