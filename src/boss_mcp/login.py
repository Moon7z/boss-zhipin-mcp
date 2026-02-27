#!/usr/bin/env python3
import argparse
import sys
from pathlib import Path
import json

sys.path.insert(0, str(Path(__file__).parent.parent))

from boss_mcp.boss_client import BossZhipinClient


def main():
    parser = argparse.ArgumentParser(description="BOSS直聘登录工具")
    parser.add_argument("--phone", "-p", required=True, help="手机号")
    parser.add_argument("--password", "-pw", required=True, help="密码")
    parser.add_argument("--headless", action="store_true", default=False, help="无头模式")
    parser.add_argument("--check", "-c", action="store_true", help="检查登录状态")
    
    args = parser.parse_args()
    
    client = BossZhipinClient(headless=args.headless)
    
    print("正在启动浏览器...")
    client.start()
    
    if args.check:
        print("检查登录状态...")
        is_logged_in = client.check_login_status()
        if is_logged_in:
            print("✓ 已登录")
        else:
            print("✗ 未登录")
        client.close()
        return
    
    print(f"请使用手机号 {args.phone} 登录BOSS直聘...")
    success = client.login(args.phone, args.password)
    
    if success:
        print("✓ 登录成功，cookies已保存")
    else:
        print("✗ 登录失败，请重试")
        sys.exit(1)
    
    client.close()


if __name__ == "__main__":
    main()
