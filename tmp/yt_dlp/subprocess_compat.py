import threading
import queue
import time
import os
import re


class subprocess:
    PIPE = -1
    STDOUT = -2
    DEVNULL = -3

    def __init__(self):
        None

    def call(target, args=(), kwargs=None):
        """
        用线程模拟 subprocess.call() 的行为。
        :param target: 要执行的目标函数
        :param args: 目标函数的位置参数（元组）
        :param kwargs: 目标函数的关键字参数（字典）
        :return: 线程任务的返回码 (0 表示成功，非 0 表示失败)
        """
        result_queue = queue.Queue()

        def thread_task():
            try:
                result = target(*args, **(kwargs or {}))  # 执行目标任务
                result_queue.put((0, result))  # 0 表示成功
            except Exception as e:
                result_queue.put((1, str(e)))  # 非 0 表示失败，保存错误信息

        # 创建线程并启动
        task_thread = threading.Thread(target=thread_task)
        task_thread.start()
        task_thread.join()  # 等待线程完成

        # 获取结果并返回退出码
        returncode, _ = result_queue.get()
        return returncode

    class Popen:
        def __init__(self, *args, **kwargs):
            """
            模拟 subprocess 的类，用线程代替进程运行任务。
            接受标准 subprocess.Popen 的参数以兼容 yt-dlp 的调用。
            """
            # 提取 env 参数（如果存在）以避免报错
            env = kwargs.pop('env', None)
            
            # 兼容原有设计：如果第一个参数是函数，则作为 target
            if args and callable(args[0]):
                self.target = args[0]
                self.args = args[1] if len(args) > 1 else ()
                self.kwargs = kwargs
            else:
                # 标准 subprocess.Popen 调用：第一个参数是命令列表
                self.target = None
                self.args = args[0] if args else ()
                self.kwargs = kwargs
            self.stdout = queue.Queue()  # 模拟标准输出
            self.stderr = queue.Queue()  # 模拟标准错误
            self.returncode = None  # 模拟返回码
            self._thread = threading.Thread(target=self._run)
            self._thread.daemon = True  # 设置线程为守护线程
            self._stop_event = threading.Event()  # 用于模拟 terminate 的停止事件
            # 自动启动线程（模拟 subprocess.Popen 的行为）
            self._thread.start()

        def _run(self):
            """
            在线程中运行目标函数，并捕获输出和返回码。
            """
            try:
                # 捕获 stdout 和 stderr
                stdout = self.kwargs.pop("stdout", None)
                stderr = self.kwargs.pop("stderr", None)

                if stdout is None:
                    stdout = self.stdout
                if stderr is None:
                    stderr = self.stderr

                # 模拟任务执行
                if self.target:
                    result = self.target(*self.args, **self.kwargs)
                    if self._stop_event.is_set():
                        raise RuntimeError("Thread terminated")
                    stdout.put(str(result))  # 模拟输出
                    self.returncode = 0  # 任务成功，返回码设为 0
                else:
                    # 标准 subprocess.Popen 调用：暂时返回成功（保持最小改动）
                    if self._stop_event.is_set():
                        raise RuntimeError("Thread terminated")
                    stdout.put("")  # 模拟输出
                    self.returncode = 0  # 任务成功，返回码设为 0
            except Exception as e:
                self.stderr.put(str(e))  # 捕获错误
                self.returncode = 1  # 任务失败，返回码设为非 0

        def start(self):
            """启动线程（如果尚未启动）"""
            if not self._thread.is_alive():
                self._thread.start()

        def wait(self, timeout=None):
            """
            等待线程完成，模拟 subprocess 的 wait 方法。
            :param timeout: 等待超时时间
            """
            self._thread.join(timeout)
            if self._thread.is_alive():
                raise TimeoutError("Thread did not finish within the timeout period.")
            return self.returncode

        def terminate(self):
            """终止线程运行，模拟 subprocess 的 terminate 方法。"""
            self._stop_event.set()
            if self._thread.is_alive():
                self._thread.join()  # 等待线程终止

        def kill(self):
            """终止线程运行，模拟 subprocess 的 kill 方法。"""
            self.terminate()

        def communicate(self, input=None, timeout=None):
            """
            等待线程完成，并返回 stdout 和 stderr 的内容。
            :param input: 写入 stdin 的数据（iOS 环境下忽略）
            :param timeout: 等待超时时间
            """
            try:
                self.wait(timeout)
            except TimeoutError:
                self.terminate()
                raise TimeoutError("Thread was terminated due to timeout.")

            stdout_content = []
            stderr_content = []
            while not self.stdout.empty():
                stdout_content.append(self.stdout.get())
            while not self.stderr.empty():
                stderr_content.append(self.stderr.get())
            return "\n".join(stdout_content), "\n".join(stderr_content)

        def poll(self):
            """
            检查线程是否完成，模拟 subprocess 的 poll。
            :return: None 表示任务未完成，或者返回 returncode
            """
            if self._thread.is_alive():
                return None
            return self.returncode
        
        def __enter__(self):
            """支持上下文管理器协议（with 语句）"""
            return self
        
        def __exit__(self, exc_type, exc_val, exc_tb):
            """支持上下文管理器协议（with 语句）"""
            # 如果线程还在运行，尝试终止它
            if self._thread.is_alive():
                self.terminate()
            return False  # 不抑制异常


# 定义要检查的模块和替换格式
MODULE_TO_CHECK = "import subprocess"


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
    return f"from {relative_import}subprocess_compat import subprocess"


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


# 主函数
def hook_subprocess():
    # 获取当前文件的目录
    current_file = os.path.abspath(__file__)
    base_dir = os.path.dirname(current_file)

    # 递归处理目录
    process_directory(base_dir)


if __name__ == '__main__':
    hook_subprocess()
