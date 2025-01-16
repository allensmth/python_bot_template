from bot.bot import Bot
from utils.git_watcher import GitWatcher

# Main function
if __name__ == "__main__":
    bot = Bot()
    
    # 启动git监控线程
    git_watcher = GitWatcher(bot)
    git_watcher.start()
    
    # 运行主bot
    bot.run()
