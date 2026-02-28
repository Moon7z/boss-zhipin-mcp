from pathlib import Path
from typing import Optional, List
from dataclasses import dataclass
from playwright.sync_api import sync_playwright, Browser, Page, BrowserContext
import time
import json
import random
import logging

from boss_mcp.anti_detection import AntiDetection, ProxyManager, RateLimiter, AntiCaptcha


logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@dataclass
class JobInfo:
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


@dataclass
class ResumeData:
    skills: List[str]
    experience_years: int
    education: str
    expected_position: str
    expected_city: str
    name: str


class BossZhipinClient:
    def __init__(
        self,
        headless: bool = False,
        use_proxy: bool = False,
        proxy_list: List[str] = None,
        enable_anti_detection: bool = True,
        max_requests_per_minute: int = 5
    ):
        self.headless = headless
        self.use_proxy = use_proxy
        self.proxy_list = proxy_list or []
        self.enable_anti_detection = enable_anti_detection
        self.max_requests_per_minute = max_requests_per_minute
        
        self.playwright = None
        self.browser: Optional[Browser] = None
        self.context: Optional[BrowserContext] = None
        self.page: Optional[Page] = None
        self.anti_detection: Optional[AntiDetection] = None
        self.proxy_manager: Optional[ProxyManager] = None
        self.rate_limiter: Optional[RateLimiter] = None
        self.anti_captcha: Optional[AntiCaptcha] = None
        
        self.cookies_path = Path(__file__).parent / "cookies.json"
        self.is_logged_in = False
        self.error_count = 0
        self.max_errors = 3
        self.risk_detected = False
        self.action_count = 0
        self.session_start_time = None
    
    def start(self):
        self.playwright = sync_playwright().start()
        
        browser_args = [
            "--disable-blink-features=AutomationControlled",
            "--disable-dev-shm-usage",
            "--no-sandbox"
        ]
        
        if self.use_proxy and self.proxy_list:
            self.proxy_manager = ProxyManager(self.proxy_list)
            proxy = self.proxy_manager.get_next_proxy()
            if proxy:
                proxy_config = self.proxy_manager.parse_proxy(proxy)
                self.browser = self.playwright.chromium.launch(
                    headless=self.headless,
                    proxy=proxy_config,
                    args=browser_args
                )
            else:
                self.browser = self.playwright.chromium.launch(headless=self.headless, args=browser_args)
        else:
            self.browser = self.playwright.chromium.launch(headless=self.headless, args=browser_args)
        
        viewport_width = random.randint(1200, 1400)
        viewport_height = random.randint(700, 900)
        
        self.context = self.browser.new_context(
            viewport={"width": viewport_width, "height": viewport_height},
            user_agent=self._generate_random_user_agent()
        )
        
        self.page = self.context.new_page()
        
        if self.enable_anti_detection:
            self.anti_detection = AntiDetection(self.page, self.context)
            self.anti_detection.randomize_browser_fingerprint()
        
        self.rate_limiter = RateLimiter(
            max_requests=self.max_requests_per_minute,
            time_window=60
        )
        self.anti_captcha = AntiCaptcha()
        
        self.load_cookies()
        self.check_login_status()
        
        self.session_start_time = time.time()
    
    def _generate_random_user_agent(self) -> str:
        versions = [
            "Chrome/120.0.0.0",
            "Chrome/121.0.0.0",
            "Chrome/122.0.0.0",
        ]
        base = random.choice(versions)
        return f"Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) {base} Safari/537.36"
    
    def _safe_delay(self, min_sec: float = 1.0, max_sec: float = 3.0):
        if self.enable_anti_detection and self.anti_detection:
            self.anti_detection.random_delay(min_sec, max_sec)
        else:
            time.sleep(random.uniform(min_sec, max_sec))
    
    def close(self):
        if self.context:
            self.context.close()
        if self.browser:
            self.browser.close()
        if self.playwright:
            self.playwright.stop()
    
    def save_cookies(self):
        if self.context and self.cookies_path:
            cookies = self.context.cookies()
            with open(self.cookies_path, "w", encoding="utf-8") as f:
                json.dump(cookies, f, ensure_ascii=False)
            logger.info("Cookies已保存")
    
    def load_cookies(self) -> bool:
        if self.cookies_path.exists():
            try:
                with open(self.cookies_path, "r", encoding="utf-8") as f:
                    cookies = json.load(f)
                self.context.add_cookies(cookies)
                logger.info("Cookies已加载")
                return True
            except Exception as e:
                logger.warning(f"加载Cookies失败: {e}")
        return False
    
    def _check_for_captcha(self) -> bool:
        if self.anti_captcha:
            if self.anti_captcha.detect_slider_captcha():
                logger.warning("检测到滑块验证码")
                return True
            if self.anti_captcha.detect_verify_code():
                logger.warning("检测到验证码")
                return True
        return False
    
    def _handle_error(self, error_msg: str):
        self.error_count += 1
        logger.error(f"错误 {self.error_count}/{self.max_errors}: {error_msg}")
        
        if self.error_count >= self.max_errors:
            raise RuntimeError(f"错误次数过多 ({self.max_errors})，请检查账号状态")
        
        wait_time = random.uniform(5, 15)
        logger.info(f"等待 {wait_time:.1f} 秒后重试...")
        time.sleep(wait_time)
    
    def login(self, phone: str, password: str) -> bool:
        if not self.page:
            raise RuntimeError("浏览器未启动，请先调用start()")
        
        logger.info("正在打开BOSS直聘登录页面...")
        self.page.goto("https://www.zhipin.com/")
        self._safe_delay(2, 4)
        
        self._check_for_captcha()
        
        try:
            if self.enable_anti_detection and self.anti_detection:
                self.anti_detection.human_click('.btn-start')
            else:
                self.page.click('.btn-start')
            
            self._safe_delay(1, 2)
            
            if self.enable_anti_detection and self.anti_detection:
                self.anti_detection.page.fill('.ipt-phone', phone)
                self._safe_delay(0.3, 0.8)
                
                self.anti_detection.page.fill('.ipt-pwd', password)
                self._safe_delay(0.3, 0.8)
                
                self.anti_detection.human_click('.btn-login')
            else:
                self.page.fill('.ipt-phone', phone)
                time.sleep(0.5)
                self.page.fill('.ipt-pwd', password)
                time.sleep(0.5)
                self.page.click('.btn-login')
            
            self._safe_delay(3, 5)
            
            if self._check_for_captcha():
                logger.warning("登录时遇到验证码，请手动处理后重试")
                return False
            
            if "web" in self.page.url or "zhipin.com" in self.page.url:
                self.save_cookies()
                self.is_logged_in = True
                logger.info("登录成功!")
                return True
            
        except Exception as e:
            self._handle_error(f"登录失败: {e}")
        
        return False
    
    def check_login_status(self) -> bool:
        try:
            if not self.page:
                return False
            
            self.page.goto('https://www.zhipin.com/', timeout=10000)
            self.page.wait_for_load_state('networkidle', timeout=5000)
            
            user_avatar = self.page.query_selector('.user-avatar')
            if user_avatar:
                self.is_logged_in = True
                return True
            
            user_avatar_img = self.page.query_selector('.header-avatar img')
            if user_avatar_img:
                self.is_logged_in = True
                return True
            
            nav_user = self.page.query_selector('.nav-user')
            if nav_user:
                self.is_logged_in = True
                return True
                
        except Exception as e:
            pass
        
        self.is_logged_in = False
        return False
    
    def _check_risk_detection(self) -> bool:
        try:
            risk_dialog = self.page.query_selector('.risk-dialog')
            if risk_dialog:
                logger.warning("检测到风控弹窗")
                self.risk_detected = True
                return True
            
            verify_dialog = self.page.query_selector('.verify-dialog')
            if verify_dialog:
                logger.warning("检测到验证弹窗")
                self.risk_detected = True
                return True
            
            forbidden = self.page.query_selector('.forbidden-page')
            if forbidden:
                logger.warning("检测到封禁页面")
                self.risk_detected = True
                return True
            
            if "captcha" in self.page.url.lower() or "verify" in self.page.url.lower():
                logger.warning("检测到验证码页面")
                self.risk_detected = True
                return True
                
        except:
            pass
        
        return False
    
    def search_jobs(
        self,
        keyword: str,
        city: str = "",
        experience: str = "",
        education: str = "",
        salary: str = "",
        page_count: int = 3
    ) -> List[JobInfo]:
        if not self.page:
            raise RuntimeError("浏览器未启动，请先调用start()")
        
        if not self.is_logged_in:
            logger.warning("未检测到登录状态，请先登录")
        
        self.rate_limiter.wait_if_needed()
        
        logger.info(f"正在搜索: {keyword} {city}")
        
        url = f"https://www.zhipin.com/web/geek/job?query={keyword}&city={city}"
        self.page.goto(url)
        self._safe_delay(2, 4)
        
        if self._check_for_captcha():
            raise RuntimeError("遇到验证码，请手动处理")
        
        if self._check_risk_detection():
            raise RuntimeError("检测到风控警告，请稍后再试")
        
        if self.enable_anti_detection and self.anti_detection:
            self.anti_detection.scroll_to_bottom(steps=random.randint(2, 4))
        
        jobs: List[JobInfo] = []
        
        for page_num in range(page_count):
            logger.info(f"正在抓取第 {page_num + 1} 页...")
            
            job_cards = self.page.query_selector_all('.job-card-wrapper')
            
            for card in job_cards:
                try:
                    title = card.query_selector('.job-title').inner_text() if card.query_selector('.job-title') else ""
                    company = card.query_selector('.company-name').inner_text() if card.query_selector('.company-name') else ""
                    salary_elem = card.query_selector('.salary')
                    salary = salary_elem.inner_text() if salary_elem else ""
                    
                    info_primary = card.query_selector('.info-primary')
                    if info_primary:
                        spans = info_primary.query_selector_all('span')
                        job_city = spans[0].inner_text() if len(spans) > 0 else ""
                        job_exp = spans[1].inner_text() if len(spans) > 1 else ""
                        job_edu = spans[2].inner_text() if len(spans) > 2 else ""
                    else:
                        job_city = job_exp = job_edu = ""
                    
                    job_id = card.get_attribute('data-jobid') or ""
                    
                    desc_elem = card.query_selector('.job-desc')
                    description = desc_elem.inner_text() if desc_elem else ""
                    
                    hr_name_elem = card.query_selector('.hr-name')
                    hr_name = hr_name_elem.inner_text() if hr_name_elem else ""
                    
                    hr_status_elem = card.query_selector('.hr-active-status')
                    hr_active_status = hr_status_elem.inner_text() if hr_status_elem else ""
                    
                    job = JobInfo(
                        job_id=job_id,
                        title=title,
                        company=company,
                        salary=salary,
                        city=job_city,
                        experience=job_exp,
                        education=job_edu,
                        description=description,
                        hr_name=hr_name,
                        hr_active_status=hr_active_status
                    )
                    jobs.append(job)
                    
                    self._safe_delay(0.1, 0.3)
                    
                except Exception as e:
                    logger.debug(f"解析岗位卡片失败: {e}")
                    continue
            
            next_btn = self.page.query_selector('.ui-pager-next')
            if next_btn and 'disabled' not in (next_btn.get_attribute('class') or ''):
                if self.enable_anti_detection and self.anti_detection:
                    self.anti_detection.human_click('.ui-pager-next')
                else:
                    next_btn.click()
                self._safe_delay(2, 4)
                
                if self.enable_anti_detection and self.anti_detection:
                    self.anti_detection.scroll_to_bottom(steps=random.randint(1, 2))
            else:
                break
        
        logger.info(f"共找到 {len(jobs)} 个岗位")
        return jobs
    
    def calculate_match_score(self, job: JobInfo, resume: ResumeData) -> int:
        score = 0
        
        job_title_lower = job.title.lower()
        job_desc_lower = job.description.lower()
        
        for skill in resume.skills:
            if skill.lower() in job_title_lower or skill.lower() in job_desc_lower:
                score += 20
        
        if resume.experience_years > 0:
            exp_match = ''.join(filter(str.isdigit, job.experience))
            if exp_match:
                job_exp = int(exp_match)
                if abs(job_exp - resume.experience_years) <= 2:
                    score += 15
        
        if resume.education:
            edu_order = {'中专': 1, '高中': 2, '大专': 3, '本科': 4, '硕士': 5, '博士': 6}
            if job.education in edu_order and resume.education in edu_order:
                if edu_order[job.education] <= edu_order[resume.education]:
                    score += 10
        
        if resume.expected_city and resume.expected_city in job.city:
            score += 10
        
        return min(score, 100)
    
    def _extract_jd_full(self, job_id: str) -> str:
        try:
            job_url = f"https://www.zhipin.com/job_detail/{job_id}.html"
            self.page.goto(job_url, timeout=10000)
            self._safe_delay(1, 2)
            
            jd_text = ""
            
            job_detail = self.page.query_selector('.job-detail')
            if job_detail:
                desc_elem = job_detail.query_selector('.job-desc')
                if desc_elem:
                    jd_text = desc_elem.inner_text()
                
                if not jd_text:
                    requirements = job_detail.query_selector_all('.requirement-item')
                    for req in requirements:
                        jd_text += req.inner_text() + " "
            
            return jd_text.strip()
        except Exception as e:
            logger.debug(f"获取JD失败: {e}")
            return ""
    
    def calculate_match_score(self, job: JobInfo, resume: ResumeData, full_jd: str = "") -> int:
        score = 0
        max_score = 100
        
        combined_text = f"{job.title} {job.description} {full_jd}".lower()
        
        resume_skills = [s.lower() for s in resume.skills]
        matched_skills = []
        missing_skills = []
        
        for skill in resume_skills:
            if skill in combined_text:
                score += 15
                matched_skills.append(skill)
            else:
                missing_skills.append(skill)
        
        score += len(matched_skills) * 5
        if len(matched_skills) >= 3:
            score += 10
        
        keywords_map = {
            'python': ['python', 'django', 'flask', 'fastapi', 'tornado'],
            'java': ['java', 'spring', 'springboot', 'mybatis'],
            '前端': ['vue', 'react', 'angular', 'javascript', 'typescript', 'html', 'css', '前端'],
            '后端': ['后端', 'api', 'rest', 'grpc', '微服务'],
            '数据库': ['mysql', 'redis', 'mongodb', 'postgresql', 'sql', '数据库'],
            '算法': ['算法', '机器学习', '深度学习', 'ai', '人工智能', 'nlp', 'cv'],
            '全栈': ['全栈', 'fullstack', '前端', '后端'],
            '测试': ['测试', '自动化', 'selenium', 'unittest', 'pytest'],
            '运维': ['运维', 'docker', 'kubernetes', 'k8s', 'linux', 'devops'],
        }
        
        for category, keywords in keywords_map.items():
            category_match = 0
            for kw in keywords:
                if kw in combined_text:
                    category_match = 1
                    break
            if category_match:
                for skill in resume_skills:
                    if any(kw in skill for kw in keywords):
                        score += 5
        
        if resume.experience_years > 0:
            exp_numbers = ''.join(filter(str.isdigit, job.experience))
            if exp_numbers:
                try:
                    job_exp = int(exp_numbers)
                    exp_diff = abs(job_exp - resume.experience_years)
                    if exp_diff == 0:
                        score += 20
                    elif exp_diff <= 1:
                        score += 15
                    elif exp_diff <= 2:
                        score += 10
                    elif exp_diff <= 3:
                        score += 5
                except:
                    pass
        
        if resume.education:
            edu_order = {'中专': 1, '高中': 2, '大专': 3, '本科': 4, '硕士': 5, '博士': 6}
            if job.education in edu_order and resume.education in edu_order:
                if edu_order[job.education] <= edu_order[resume.education]:
                    score += 15
                else:
                    score -= 10
        
        if resume.expected_city and resume.expected_city in job.city:
            score += 10
        
        if '急招' in job.title or '急聘' in job.title:
            score += 5
        
        if '面试' in job.description or '面试' in full_jd:
            score += 5
        
        score = max(0, min(score, max_score))
        
        return score
    
    def greet_hr(self, job: JobInfo, resume: ResumeData, custom_message: str = "") -> bool:
        if not self.page:
            raise RuntimeError("浏览器未启动，请先调用start()")
        
        if self.risk_detected:
            logger.warning("检测到风控，请勿继续操作")
            return False
        
        if self.action_count >= 20:
            logger.warning("单次会话打招呼次数已达上限(20)，请明天再试")
            return False
        
        session_duration = time.time() - (self.session_start_time or time.time())
        if session_duration > 1800:
            logger.warning("会话时长超过30分钟，请重新登录")
            return False
        
        job_url = f"https://www.zhipin.com/job_detail/{job.job_id}.html"
        self.page.goto(job_url)
        self._safe_delay(2, 3)
        
        if self._check_for_captcha():
            logger.warning("打招呼时遇到验证码")
            return False
        
        if self._check_risk_detection():
            logger.warning("打招呼时检测到风控")
            return False
        
        try:
            contact_btn = self.page.query_selector('.btn-startchat')
            if contact_btn:
                if self.enable_anti_detection and self.anti_detection:
                    self.anti_detection.human_click('.btn-startchat')
                else:
                    contact_btn.click()
                
                self._safe_delay(1, 2)
            
            if custom_message:
                msg_box = self.page.query_selector('.msg-textarea')
                if msg_box:
                    if self.enable_anti_detection and self.anti_detection:
                        self.anti_detection.page.fill('.msg-textarea', custom_message)
                    else:
                        msg_box.fill(custom_message)
                    
                    self._safe_delay(0.5, 1)
            
            send_btn = self.page.query_selector('.btn-send')
            if send_btn:
                if self.enable_anti_detection and self.anti_detection:
                    self.anti_detection.human_click('.btn-send')
                else:
                    send_btn.click()
                
                self._safe_delay(1, 2)
                logger.info(f"已向 {job.company} 的HR发送打招呼消息")
                self.action_count += 1
                return True
                
        except Exception as e:
            logger.error(f"打招呼失败: {e}")
        
        return False
    
    def batch_greet(
        self,
        jobs: List[JobInfo],
        resume: ResumeData,
        min_score: int = 30,
        custom_message_template: str = ""
    ) -> dict:
        results = {
            "total": len(jobs),
            "matched": 0,
            "greeted": 0,
            "failed": 0,
            "details": []
        }
        
        default_message = (
            f"您好！我是{resume.name or '求职者'}，"
            f"我对您发布的{job.title}岗位很感兴趣。"
            f"我的技能包括{', '.join(resume.skills[:5])}，"
            f"有{resume.experience_years}年工作经验。"
            f"期待与您进一步沟通！"
        )
        
        message = custom_message_template or default_message
        
        for i, job in enumerate(jobs):
            logger.info(f"处理第 {i+1}/{len(jobs)} 个岗位: {job.company}")
            
            score = self.calculate_match_score(job, resume)
            detail = {
                "job": job.title,
                "company": job.company,
                "score": score,
                "status": "skipped"
            }
            
            if score >= min_score:
                results["matched"] += 1
                
                self.rate_limiter.wait_if_needed()
                
                success = self.greet_hr(job, resume, message)
                
                if success:
                    results["greeted"] += 1
                    detail["status"] = "success"
                else:
                    results["failed"] += 1
                    detail["status"] = "failed"
            
            results["details"].append(detail)
            
            self._safe_delay(2, 5)
        
        logger.info(f"批量打招呼完成: 匹配{results['matched']}, 成功{results['greeted']}, 失败{results['failed']}")
        return results
