import os
import sys
import json
import threading


class SwiftPythonBridge:
    # 类变量（静态变量），存储全局实例
    _instance = None

    def __init__(self):
        print("SwiftBridge init")
        None

    @classmethod
    def get_instance(cls):
        """
        获取全局 SwiftPythonBridge 实例（单例模式）
        
        Returns:
            SwiftPythonBridge: 全局 SwiftPythonBridge 实例
        """
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    @classmethod
    def set_instance(cls, instance):
        """
        设置全局 SwiftPythonBridge 实例
        
        Args:
            instance: SwiftPythonBridge 实例
        """
        cls._instance = instance

    def test(self):
        jsCode = "let a = 1; let b = 2; a+b;"
        current_thread = threading.current_thread()
        print(f"Current thread name: {current_thread.name}, thread id: {current_thread.ident}")
        result = self.callSwiftExecJs(jsCode)
        print("result from swift:" + result)
        None

    def remoteCipherJCP(self, jsCode):
        # 调用 swift 执行 js 解密 签名和 n 参数
        # 执行时被 swift 替换为实际的代码
        # json payload 结构：
        # jsonPayload = {
        #     'player_url': player_url,           // 播放器 js 代码链接
        #     'encrypted_signature': sig_value,   // 加密的签名
        #     'n_param': n_value,                 // 加密的 n 参数
        #     'player_code': player_code,         // 播放器 js 代码
        #     'ejs_code': ejs_code,               // ejs 处理打包后的 standalone 代码
        # }
        # json 参数需要先用 json.dumps() 序列化再传给 swift
        print("swift 暂未实现")
        return json.dumps({
            "error": "暂未实现"
        })


    def callSwiftExecJs(self, jsCode):
        # 调用 swift 执行 js 代码并返回结果
        # 执行时被 swift 替换为实际的代码
        None
