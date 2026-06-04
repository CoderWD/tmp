"""
兼容的 sysconfig 模块实现
用于 iOS 等缺少 _sysconfigdata 模块的环境
"""
import os


class sysconfig:
    """兼容的 sysconfig 类，模拟标准库 sysconfig 模块的行为"""
    
    @staticmethod
    def get_path(scheme, vars=None, expand=True):
        """返回指定 scheme 的路径"""
        return '.'
    
    @staticmethod
    def get_config_var(name, default=None):
        """返回配置变量的值"""
        return default if default is not None else ''


# 定义要检查的模块和替换格式
MODULE_TO_CHECK = "import sysconfig"


# 获取相对于基准文件的相对路径导入语句
def generate_relative_import(base_dir, target_dir):
    base_parts = base_dir.split(os.sep)
    target_parts = target_dir.split(os.sep)

    # 找到公共路径前缀的长度
    common_length = 0
    for base_part, target_part in zip(base_parts, target_parts):
        if base_part == target_part:
            common_length += 1
        else:
            break

    # 计算相对层级并构造相对导入路径
    upward_levels = len(target_parts) - common_length
    relative_import = "." * (upward_levels + 1)  # +1 是为了覆盖同级情况也正确
    return f"from {relative_import}sysconfig_compat import sysconfig"


# 递归检查和修改 .py 文件
def process_directory(base_dir):
    for root, _, files in os.walk(base_dir):
        for file in files:
            if file.endswith(".py"):
                file_path = os.path.join(root, file)
                update_imports(base_dir, file_path)


# 更新文件中的导入语句
def update_imports(base_dir, file_path):
    new_import = generate_relative_import(base_dir, os.path.dirname(file_path))

    with open(file_path, "r", encoding="utf-8") as f:
        lines = f.readlines()

    updated_lines = []
    modified = False

    for line in lines:
        # 精确匹配只有 MODULE_TO_CHECK 的行
        if line.strip() == MODULE_TO_CHECK:
            updated_lines.append(f"{new_import}\n")
            modified = True
        else:
            updated_lines.append(line)

    if modified:
        with open(file_path, "w", encoding="utf-8") as f:
            f.writelines(updated_lines)
        return True
    return False


# 主函数
def hook_sysconfig():
    # 获取当前文件的目录
    current_file = os.path.abspath(__file__)
    base_dir = os.path.dirname(current_file)
    
    # 预期的文件列表（只有这些文件应该被修改）
    expected_files = ['utils/_jsruntime.py']
    
    # 记录修改的文件
    modified_files = []

    print("=" * 70)
    print("开始 hook sysconfig 模块...")
    print("=" * 70)
    
    # 递归处理目录
    for root, _, files in os.walk(base_dir):
        for file in files:
            if file.endswith(".py"):
                file_path = os.path.join(root, file)
                if update_imports(base_dir, file_path):
                    # 计算相对路径用于显示
                    rel_path = os.path.relpath(file_path, base_dir)
                    modified_files.append(rel_path)
                    print(f"✓ 已修改: {rel_path}")
    
    print("=" * 70)
    print(f"总共修改了 {len(modified_files)} 个文件")
    print("=" * 70)
    
    # 检查是否有意外的文件被修改
    unexpected_files = []
    for file_path in modified_files:
        # 检查是否在预期列表中
        is_expected = any(file_path.endswith(expected) for expected in expected_files)
        if not is_expected:
            unexpected_files.append(file_path)
    
    if unexpected_files:
        print("\n" + "!" * 70)
        print("⚠️  警告：发现以下非预期文件被修改，请检查：")
        print("!" * 70)
        for file_path in unexpected_files:
            print(f"  ⚠️  {file_path}")
        print("!" * 70)
        print()
    else:
        print("✓ 所有修改的文件都在预期列表中")
    
    print("hook sysconfig 完成！")
    print("=" * 70)


if __name__ == '__main__':
    hook_sysconfig()
