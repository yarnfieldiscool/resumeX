"""
Quick Test Suite for All Modules

运行所有模块的内置测试示例，验证功能完整性。
"""

import sys


def test_module(module_name: str):
    """运行单个模块的测试"""
    print(f"\n{'='*60}")
    print(f"Testing: {module_name}")
    print('='*60)

    try:
        # 动态导入并执行模块的 __main__ 代码
        import importlib.util
        spec = importlib.util.spec_from_file_location(module_name, f"{module_name}.py")
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        print(f"[OK] {module_name} test passed\n")
        return True
    except Exception as e:
        print(f"[FAIL] {module_name} test failed: {e}\n")
        return False


def main():
    """运行所有模块测试"""
    modules = [
        "source_grounding",
        "overlap_dedup",
        "confidence_scorer",
        "entity_resolver",
        "relation_inferrer",
        "kg_injector",
    ]

    print("Running all module tests...")
    print("="*60)

    results = {}
    for module in modules:
        results[module] = test_module(module)

    # 汇总
    print("\n" + "="*60)
    print("Test Summary")
    print("="*60)

    passed = sum(1 for r in results.values() if r)
    total = len(results)

    for module, success in results.items():
        status = "[OK]  " if success else "[FAIL]"
        print(f"{status} {module}")

    print(f"\nTotal: {passed}/{total} passed")

    if passed == total:
        print("\nAll tests passed!")
        sys.exit(0)
    else:
        print(f"\n{total - passed} test(s) failed")
        sys.exit(1)


if __name__ == "__main__":
    main()
