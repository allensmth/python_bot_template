import threading
import subprocess
import time
import os
import sys

class GitWatcher(threading.Thread):
    def __init__(self, bot_instance):
        super().__init__()
        self.bot = bot_instance
        self.daemon = True
        self.running = True

    def run(self):
        while self.running:
            # 检查git状态
            status = subprocess.run(['git', 'fetch'], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            status = subprocess.run(['git', 'status', '-uno'], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            
            # 如果有更新
            if b'Your branch is behind' in status.stdout:
                print("检测到代码更新，正在拉取最新代码...")
                subprocess.run(['git', 'pull'])
                print("代码更新完成，正在重启bot...")
                
                # 重启bot
                self.bot.stop()
                os.execv(sys.executable, ['python'] + [sys.argv[0]])
            
            # 每10秒检查一次
            time.sleep(10)