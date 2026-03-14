import sys
sys.path.insert(0, 'src/boss_mcp/v3')

print("🧪 测试融合版v3...")

try:
    from server_v3 import state, FASTMCP_AVAILABLE
    print(f"✅ FastMCP可用: {FASTMCP_AVAILABLE}")
    print(f"✅ 状态管理: {type(state).__name__}")
    
    # 测试功能
    from server_v3 import login_by_password, search_jobs
    result = login_by_password("13800138000", "test")
    print(f"✅ 登录测试: {result['success']}")
    
    result = search_jobs("Python", "北京")
    print(f"✅ 搜索测试: {result['success']}")
    
    print("\n🎉 测试通过！")
    
except Exception as e:
    print(f"\n❌ 失败: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)
