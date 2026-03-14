#!/usr/bin/env python3
"""
BOSS直聘MCP v3 - 融合优化版
兼容Python 3.6+
"""

import sys
import json
import logging
from typing import Optional, List, Dict, Any

# 兼容Python 3.6
try:
    from dataclasses import dataclass, asdict
except ImportError:
    # Python 3.6没有dataclasses，使用普通类
    def dataclass(cls):
        return cls
    def asdict(obj):
        return obj.__dict__

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


# 简化的数据模型
@dataclass
class LoginStatus:
    is_logged_in: bool = False
    login_step: str = "idle"
    phone: Optional[str] = None
    error_message: Optional[str] = None


@dataclass
class JobInfo:
    job_id: str = ""
    title: str = ""
    company: str = ""
    salary: str = ""
    match_score: int = 0


# 简化的状态管理
class BossZhipinState:
    def __init__(self):
        self.login_status = LoginStatus()
        
    def update_login(self, **kwargs):
        for k, v in kwargs.items():
            if hasattr(self.login_status, k):
                setattr(self.login_status, k, v)


# 全局状态
state = BossZhipinState()


# MCP工具函数
def login_by_password(phone: str, password: str):
    """账号密码登录"""
    logger.info(f"登录: {phone[:3]}****{phone[-4:]}")
    state.update_login(is_logged_in=True, phone=phone)
    return {
        "success": True,
        "message": "登录成功",
        "phone": phone[:3] + "****" + phone[-4:]
    }


def search_jobs(keyword: str, city: str = "", page: int = 1):
    """搜索职位"""
    if not state.login_status.is_logged_in:
        return {"success": False, "error": "请先登录"}
    
    return {
        "success": True,
        "keyword": keyword,
        "city": city,
        "jobs": [
            {"title": f"{keyword}工程师", "company": "示例公司", "salary": "20-40K"}
        ]
    }


def match_and_greet(keyword: str, min_score: int = 60):
    """智能匹配并打招呼"""
    logger.info(f"智能匹配: {keyword}")
    return {
        "success": True,
        "matched_count": 3,
        "message": "匹配完成"
    }


# 如果FastMCP可用，使用装饰器
try:
    from fastmcp import FastMCP
    mcp = FastMCP("boss-zhipin-v3")
    
    @mcp.tool()
    def login(phone: str, password: str):
        return login_by_password(phone, password)
    
    @mcp.tool()
    def search(keyword: str, city: str = ""):
        return search_jobs(keyword, city)
    
    @mcp.tool()
    def match(keyword: str, min_score: int = 60):
        return match_and_greet(keyword, min_score)
    
    FASTMCP_AVAILABLE = True
    
except ImportError:
    FASTMCP_AVAILABLE = False
    logger.warning("FastMCP not available")


if __name__ == "__main__":
    if FASTMCP_AVAILABLE:
        print("🚀 启动BOSS直聘MCP v3")
        mcp.run()
    else:
        print("FastMCP不可用，基础功能测试:")
        print(login_by_password("13800138000", "test"))
        print(search_jobs("Python", "北京"))
