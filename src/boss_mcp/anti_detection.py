import random
import time
from typing import Optional
from playwright.sync_api import Page, BrowserContext


class AntiDetection:
    def __init__(self, page: Page, context: BrowserContext):
        self.page = page
        self.context = context
        self.min_delay = 0.5
        self.max_delay = 2.0
        self.min_scroll_pause = 0.3
        self.max_scroll_pause = 0.8
    
    def random_delay(self, min_sec: Optional[float] = None, max_sec: Optional[float] = None):
        min_d = min_sec or self.min_delay
        max_d = max_sec or self.max_delay
        delay = random.uniform(min_d, max_d)
        time.sleep(delay)
    
    def human_scroll(self, direction: str = "down", distance: Optional[int] = None):
        if direction == "down":
            if distance is None:
                distance = random.randint(200, 500)
            self.page.evaluate(f"window.scrollBy(0, {distance})")
        else:
            if distance is None:
                distance = random.randint(200, 500)
            self.page.evaluate(f"window.scrollBy(0, -{distance})")
        
        self.random_delay(self.min_scroll_pause, self.max_scroll_pause)
    
    def scroll_to_bottom(self, steps: int = 5):
        for _ in range(steps):
            self.human_scroll("down", random.randint(300, 600))
            if random.random() > 0.7:
                self.human_scroll("up", random.randint(100, 200))
    
    def scroll_to_element(self, selector: str):
        try:
            self.page.locator(selector).first.scroll_into_view_if_needed()
            self.random_delay(0.3, 0.8)
        except:
            pass
    
    def human_mouse_move(self, target_x: int, target_y: int):
        current_x = random.randint(0, 500)
        current_y = random.randint(0, 800)
        
        steps = random.randint(10, 20)
        for i in range(steps):
            progress = (i + 1) / steps
            x = int(current_x + (target_x - current_x) * progress + random.randint(-10, 10))
            y = int(current_y + (target_y - current_y) * progress + random.randint(-10, 10))
            
            self.page.mouse.move(x, y)
            time.sleep(random.uniform(0.02, 0.05))
        
        self.random_delay(0.1, 0.3)
    
    def human_click(self, selector: str):
        try:
            element = self.page.locator(selector).first
            bbox = element.bounding_box()
            
            if bbox:
                x = int(bbox["x"] + bbox["width"] / 2 + random.randint(-5, 5))
                y = int(bbox["y"] + bbox["height"] / 2 + random.randint(-5, 5))
                
                self.human_mouse_move(x, y)
                time.sleep(random.uniform(0.1, 0.2))
                
                self.page.mouse.click(x, y)
            else:
                element.click()
            
            self.random_delay(0.3, 0.8)
        except Exception as e:
            raise RuntimeError(f"点击元素失败: {e}")
    
    def human_hover(self, selector: str):
        try:
            element = self.page.locator(selector).first
            bbox = element.bounding_box()
            
            if bbox:
                x = int(bbox["x"] + bbox["width"] / 2 + random.randint(-10, 10))
                y = int(bbox["y"] + bbox["height"] / 2 + random.randint(-10, 10))
                
                self.page.mouse.move(x, y)
            
            self.random_delay(0.5, 1.5)
        except:
            pass
    
    def randomize_browser_fingerprint(self):
        viewport = self.context.viewport_size
        if viewport:
            new_width = viewport["width"] + random.randint(-50, 50)
            new_height = viewport["height"] + random.randint(-50, 50)
            self.context.set_viewport_size({"width": new_width, "height": new_height})
        
        self.page.add_init_script("""
            Object.defineProperty(navigator, 'webdriver', {
                get: () => undefined
            });
            
            Object.defineProperty(navigator, 'plugins', {
                get: () => [1, 2, 3, 4, 5]
            });
            
            Object.defineProperty(navigator, 'languages', {
                get: () => ['zh-CN', 'zh', 'en-US', 'en']
            });
            
            Object.defineProperty(navigator, 'hardwareConcurrency', {
                get: () => [4, 8, 16][Math.floor(Math.random() * 3)]
            });
            
            Object.defineProperty(navigator, 'deviceMemory', {
                get: () => [4, 8, 16][Math.floor(Math.random() * 3)]
            });
            
            window.chrome = {
                runtime: {}
            };
            
            const originalQuery = window.navigator.permissions.query;
            window.navigator.permissions.query = (parameters) => (
                parameters.name === 'notifications' ?
                    Promise.resolve({ state: Notification.permission }) :
                    originalQuery(parameters)
            );
            
            Object.defineProperty(Notification, 'permission', {
                get: () => 'default'
            });
            
            if (window.navigator.mediaDevices) {
                window.navigator.mediaDevices.enumerateDevices = () => Promise.resolve([
                    { deviceId: 'default', kind: 'audioinput', label: 'Microphone' },
                    { deviceId: 'default', kind: 'videoinput', label: 'Camera' }
                ]);
            }
        """)
    
    def set_proxy(self, proxy_server: str, username: Optional[str] = None, password: Optional[str] = None):
        pass


class ProxyManager:
    def __init__(self, proxies: list[str] = None):
        self.proxies = proxies or []
        self.current_index = 0
    
    def get_next_proxy(self) -> Optional[str]:
        if not self.proxies:
            return None
        
        proxy = self.proxies[self.current_index]
        self.current_index = (self.current_index + 1) % len(self.proxies)
        return proxy
    
    def parse_proxy(self, proxy: str) -> dict:
        parts = proxy.split("://")
        protocol = parts[0] if len(parts) > 1 else "http"
        
        auth_host = parts[-1].split("@") if "@" in parts[-1] else [None, parts[-1]]
        
        auth = auth_host[0].split(":") if auth_host[0] else [None, None]
        host_port = auth_host[1].split(":") if ":" in auth_host[1] else [auth_host[1], "80"]
        
        return {
            "server": f"{protocol}://{host_port[0]}:{host_port[1]}",
            "username": auth[0],
            "password": auth[1]
        }
    
    def load_from_file(self, filepath: str):
        with open(filepath, "r", encoding="utf-8") as f:
            self.proxies = [line.strip() for line in f if line.strip()]


class RateLimiter:
    def __init__(self, max_requests: int = 10, time_window: int = 60):
        self.max_requests = max_requests
        self.time_window = time_window
        self.requests = []
    
    def can_proceed(self) -> bool:
        now = time.time()
        self.requests = [req_time for req_time in self.requests if now - req_time < self.time_window]
        
        if len(self.requests) < self.max_requests:
            self.requests.append(now)
            return True
        return False
    
    def wait_if_needed(self):
        while not self.can_proceed():
            wait_time = random.uniform(2, 5)
            time.sleep(wait_time)
        
        time.sleep(random.uniform(0.5, 2.0))
    
    def random_delay_between_actions(self):
        delay = random.uniform(1.0, 3.0)
        time.sleep(delay)


class AntiCaptcha:
    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key
    
    def detect_slider_captcha(self) -> bool:
        try:
            slider_button = self.page.query_selector('.geetest_slider_button')
            if slider_button:
                return True
        except:
            pass
        return False
    
    def detect_verify_code(self) -> bool:
        try:
            verify_elements = self.page.query_selector_all('[class*="verify"], [id*="verify"], .captcha')
            return len(verify_elements) > 0
        except:
            pass
        return False
    
    def handle_captcha(self) -> bool:
        if self.detect_slider_captcha():
            return self.solve_slider_captcha()
        elif self.detect_verify_code():
            return False
        return False
    
    def solve_slider_captcha(self) -> bool:
        return False
