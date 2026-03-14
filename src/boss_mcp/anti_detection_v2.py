"""
BOSS直聘增强版反检测模块

针对BOSS直聘强反爬机制的专项优化：
1. 浏览器指纹深度伪装
2. 行为模式人类化
3. 智能请求调度
4. 多维度风控规避
"""

import random
import time
import asyncio
import json
import hashlib
from typing import Optional, List, Dict, Any
from dataclasses import dataclass
from datetime import datetime, timedelta
import logging

logger = logging.getLogger(__name__)


@dataclass
class BrowserFingerprint:
    """浏览器指纹配置"""
    user_agent: str
    viewport: Dict[str, int]
    device_pixel_ratio: float
    hardware_concurrency: int
    device_memory: int
    language: str
    languages: List[str]
    timezone: str
    platform: str
    vendor: str
    
    @classmethod
    def random(cls) -> "BrowserFingerprint":
        """生成随机指纹"""
        viewports = [
            {"width": 1920, "height": 1080},
            {"width": 1366, "height": 768},
            {"width": 1440, "height": 900},
            {"width": 1536, "height": 864},
            {"width": 1280, "height": 720},
        ]
        
        user_agents = [
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36 Edg/119.0.0.0",
        ]
        
        return cls(
            user_agent=random.choice(user_agents),
            viewport=random.choice(viewports),
            device_pixel_ratio=random.choice([1.0, 1.25, 1.5, 2.0]),
            hardware_concurrency=random.choice([4, 8, 12, 16]),
            device_memory=random.choice([4, 8, 16, 32]),
            language="zh-CN",
            languages=["zh-CN", "zh", "en-US", "en"],
            timezone="Asia/Shanghai",
            platform=random.choice(["Win32", "MacIntel"]),
            vendor="Google Inc.",
        )


class BehaviorSimulator:
    """人类行为模拟器"""
    
    def __init__(self):
        self.reading_patterns = self._generate_reading_patterns()
        self.typing_patterns = self._generate_typing_patterns()
        self.scroll_patterns = self._generate_scroll_patterns()
        
    def _generate_reading_patterns(self) -> List[Dict]:
        """生成阅读模式"""
        return [
            {"min_time": 2, "max_time": 5, "scroll_pause": 0.5},  # 快速浏览
            {"min_time": 5, "max_time": 10, "scroll_pause": 1.0},  # 正常阅读
            {"min_time": 10, "max_time": 20, "scroll_pause": 2.0},  # 仔细阅读
        ]
    
    def _generate_typing_patterns(self) -> List[Dict]:
        """生成打字模式"""
        return [
            {"wpm": 40, "error_rate": 0.05},   # 慢速打字
            {"wpm": 60, "error_rate": 0.03},   # 正常打字
            {"wpm": 80, "error_rate": 0.02},   # 快速打字
        ]
    
    def _generate_scroll_patterns(self) -> List[Dict]:
        """生成滚动模式"""
        return [
            {"distance": (100, 300), "speed": "slow", "pause": (0.5, 1.5)},
            {"distance": (300, 600), "speed": "normal", "pause": (0.3, 0.8)},
            {"distance": (600, 1000), "speed": "fast", "pause": (0.2, 0.5)},
        ]
    
    def get_reading_time(self, content_length: int) -> float:
        """根据内容长度计算阅读时间"""
        # 平均阅读速度：200字/分钟
        base_time = content_length / 200 * 60
        pattern = random.choice(self.reading_patterns)
        return base_time * random.uniform(0.8, 1.2) + random.uniform(pattern["min_time"], pattern["max_time"])
    
    def get_typing_delay(self, char: str) -> float:
        """计算打字延迟"""
        pattern = random.choice(self.typing_patterns)
        base_delay = 60 / pattern["wpm"] / 5  # 每字符基础延迟
        
        # 特殊字符延迟
        if char in '.,!?;:\'"':
            base_delay *= 2
        elif char == ' ':
            base_delay *= 1.5
        elif char.isupper():
            base_delay *= 1.3
        
        # 随机波动
        return base_delay * random.uniform(0.8, 1.2)
    
    def get_scroll_distance(self) -> int:
        """获取滚动距离"""
        pattern = random.choice(self.scroll_patterns)
        return random.randint(*pattern["distance"])
    
    def get_scroll_pause(self) -> float:
        """获取滚动暂停时间"""
        pattern = random.choice(self.scroll_patterns)
        return random.uniform(*pattern["pause"])


class SmartScheduler:
    """智能请求调度器"""
    
    def __init__(self):
        self.daily_stats = {
            "applications": 0,
            "views": 0,
            "searches": 0,
        }
        self.hourly_limits = {
            "applications": 5,   # 每小时最多5个打招呼
            "views": 50,         # 每小时最多50个浏览
            "searches": 10,      # 每小时最多10次搜索
        }
        self.daily_limits = {
            "applications": 30,  # 每天最多30个打招呼
            "views": 300,        # 每天最多300个浏览
            "searches": 50,      # 每天最多50次搜索
        }
        self.request_history: List[Dict] = []
        
    def can_execute(self, action_type: str) -> bool:
        """检查是否可以执行操作"""
        now = datetime.now()
        
        # 检查小时限制
        hour_ago = now - timedelta(hours=1)
        hour_count = sum(1 for r in self.request_history 
                        if r["type"] == action_type and r["time"] > hour_ago)
        
        if hour_count >= self.hourly_limits.get(action_type, 10):
            logger.warning(f"{action_type} 达到小时限制")
            return False
        
        # 检查日限制
        day_ago = now - timedelta(days=1)
        day_count = sum(1 for r in self.request_history 
                       if r["type"] == action_type and r["time"] > day_ago)
        
        if day_count >= self.daily_limits.get(action_type, 100):
            logger.warning(f"{action_type} 达到日限制")
            return False
        
        return True
    
    def record(self, action_type: str):
        """记录操作"""
        self.request_history.append({
            "type": action_type,
            "time": datetime.now(),
        })
        
        # 清理过期记录
        day_ago = datetime.now() - timedelta(days=2)
        self.request_history = [r for r in self.request_history if r["time"] > day_ago]
    
    def get_wait_time(self, action_type: str) -> float:
        """获取建议等待时间"""
        base_delays = {
            "applications": (30, 60),    # 打招呼间隔30-60秒
            "views": (2, 5),              # 浏览间隔2-5秒
            "searches": (10, 20),         # 搜索间隔10-20秒
        }
        return random.uniform(*base_delays.get(action_type, (5, 10)))


class RiskDetector:
    """风险检测器"""
    
    def __init__(self):
        self.risk_signals = []
        self.risk_threshold = 0.7
        
    def detect_page_risk(self, page_content: str) -> Dict[str, Any]:
        """检测页面风险信号"""
        risk_indicators = {
            "verify_code": ["验证码", "verify", "captcha", "滑块"],
            "login_required": ["登录", "login", "请登录"],
            "blocked": ["访问频繁", "操作频繁", "已被限制", "封禁"],
            "error": ["系统错误", "服务异常", "error"],
        }
        
        detected = {}
        for risk_type, keywords in risk_indicators.items():
            if any(kw in page_content for kw in keywords):
                detected[risk_type] = True
        
        return {
            "has_risk": len(detected) > 0,
            "risk_types": list(detected.keys()),
            "risk_level": len(detected) / len(risk_indicators),
        }
    
    def detect_behavior_risk(self, actions: List[Dict]) -> float:
        """检测行为风险分数"""
        if len(actions) < 3:
            return 0.0
        
        risk_score = 0.0
        
        # 检测过于规律的间隔
        intervals = [actions[i+1]["time"] - actions[i]["time"] 
                    for i in range(len(actions)-1)]
        if len(set(intervals)) < len(intervals) * 0.3:
            risk_score += 0.3
        
        # 检测过快操作
        fast_actions = sum(1 for a in actions if a["duration"] < 1)
        if fast_actions / len(actions) > 0.5:
            risk_score += 0.3
        
        # 检测重复操作
        action_types = [a["type"] for a in actions]
        repeats = len(action_types) - len(set(action_types))
        if repeats / len(action_types) > 0.3:
            risk_score += 0.2
        
        return min(risk_score, 1.0)


class AntiDetectionV2:
    """增强版反检测主类"""
    
    def __init__(self, page=None, context=None):
        self.page = page
        self.context = context
        self.fingerprint = BrowserFingerprint.random()
        self.behavior = BehaviorSimulator()
        self.scheduler = SmartScheduler()
        self.risk_detector = RiskDetector()
        self.session_start = datetime.now()
        
    async def setup_stealth(self):
        """设置隐身模式"""
        if not self.page:
            return
        
        # 注入高级反检测脚本
        await self.page.add_init_script("""
            // 覆盖webdriver检测
            Object.defineProperty(navigator, 'webdriver', {
                get: () => undefined,
                configurable: true
            });
            
            // 覆盖权限API
            const originalQuery = window.navigator.permissions.query;
            window.navigator.permissions.query = (parameters) => {
                if (parameters.name === 'notifications') {
                    return Promise.resolve({ state: 'default' });
                }
                return originalQuery(parameters);
            };
            
            // 覆盖插件检测
            Object.defineProperty(navigator, 'plugins', {
                get: () => {
                    return [
                        {name: 'Chrome PDF Plugin', filename: 'internal-pdf-viewer'},
                        {name: 'Native Client', filename: 'native-client.mf'},
                    ];
                }
            });
            
            // 覆盖mimeTypes
            Object.defineProperty(navigator, 'mimeTypes', {
                get: () => [
                    {type: 'application/pdf', suffixes: 'pdf', enabledPlugin: {}},
                    {type: 'application/x-google-chrome-pdf', suffixes: 'pdf', enabledPlugin: {}},
                ]
            });
            
            // 覆盖canvas指纹
            const originalToDataURL = HTMLCanvasElement.prototype.toDataURL;
            HTMLCanvasElement.prototype.toDataURL = function(type) {
                if (type === 'image/png' && this.width > 16 && this.height > 16) {
                    // 添加随机噪点
                    const ctx = this.getContext('2d');
                    const imageData = ctx.getImageData(0, 0, this.width, this.height);
                    for (let i = 0; i < imageData.data.length; i += 4) {
                        imageData.data[i] += Math.random() > 0.5 ? 1 : -1;
                    }
                    ctx.putImageData(imageData, 0, 0);
                }
                return originalToDataURL.apply(this, arguments);
            };
            
            // 覆盖WebGL指纹
            const getParameter = WebGLRenderingContext.prototype.getParameter;
            WebGLRenderingContext.prototype.getParameter = function(parameter) {
                if (parameter === 37445) {
                    return 'Intel Inc.';
                }
                if (parameter === 37446) {
                    return 'Intel Iris OpenGL Engine';
                }
                return getParameter(parameter);
            };
        """)
        
        # 设置视口
        await self.page.set_viewport_size(self.fingerprint.viewport)
        
        # 设置User-Agent
        await self.page.set_extra_http_headers({
            "User-Agent": self.fingerprint.user_agent,
            "Accept-Language": ",".join(self.fingerprint.languages),
        })
    
    async def human_delay(self, min_sec: float = 1.0, max_sec: float = 3.0):
        """人类化延迟"""
        delay = random.uniform(min_sec, max_sec)
        
        # 根据时间段调整延迟（模拟工作时间规律）
        hour = datetime.now().hour
        if hour in [12, 13]:  # 午休时间
            delay *= 1.5
        elif hour in [9, 10, 14, 15]:  # 工作时间
            delay *= 1.0
        else:  # 其他时间
            delay *= 0.8
        
        await asyncio.sleep(delay)
    
    async def smart_scroll(self, page):
        """智能滚动"""
        # 模拟人类阅读滚动
        scroll_count = random.randint(3, 8)
        
        for _ in range(scroll_count):
            distance = self.behavior.get_scroll_distance()
            
            # 随机滚动方向
            if random.random() > 0.7:
                # 偶尔向上滚动（回看内容）
                await page.evaluate(f"window.scrollBy(0, -{distance // 2})")
                await self.human_delay(0.5, 1.5)
            
            # 向下滚动
            await page.evaluate(f"window.scrollBy(0, {distance})")
            
            # 阅读暂停
            pause = self.behavior.get_scroll_pause()
            await asyncio.sleep(pause)
    
    async def check_risk(self, page_content: str) -> bool:
        """检查风险"""
        risk = self.risk_detector.detect_page_risk(page_content)
        
        if risk["has_risk"]:
            logger.warning(f"检测到风险: {risk['risk_types']}, 级别: {risk['risk_level']}")
            
            if risk["risk_level"] > self.risk_detector.risk_threshold:
                return False
        
        return True
    
    def should_stop(self) -> bool:
        """判断是否应该停止"""
        session_duration = (datetime.now() - self.session_start).total_seconds()
        
        # 会话时长限制（2-4小时）
        if session_duration > random.uniform(7200, 14400):
            logger.info("会话时长达到限制，建议休息")
            return True
        
        return False
