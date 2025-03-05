from threading import Thread
import asyncio
from datetime import datetime, timedelta
from server import run_server  # Flask 服务器
from config import login
from mta import *
'''
# 获取下一个整点或半点（秒设置为 5）
def get_next_half_hour():
    now = datetime.now()
    
    if now.minute < 30:
        next_time = now.replace(minute=30, second=5, microsecond=0)
    else:
        # 如果当前时间在 30 分钟之后，添加 1 小时
        next_time = now.replace(minute=0, second=5, microsecond=0) + timedelta(hours=1)
    
    return next_time

async def wait_until(target_hour, target_minute):
    now = datetime.now()
    target_time = now.replace(hour=target_hour, minute=target_minute, second=5, microsecond=0)

    if now >= target_time:
        target_time += timedelta(days=1)  # 如果已经过了这个时间，则等到第二天

    wait_seconds = (target_time - now).total_seconds()
    await asyncio.sleep(wait_seconds)

async def wait_until_half_hour():
    now = datetime.now()
    next_time = get_next_half_hour()
    
    # 等待直到下一个整点或半点
    wait_seconds = (next_time - now).total_seconds()
    await asyncio.sleep(wait_seconds)

async def run_trading():   
    trade_count = 0  # 初始化交易次数计数器
    
    while True:
        try:
            now = datetime.now()
            is_saturday = now.weekday() == 5  # 星期六 (0=星期一, 5=星期六)

            # 处理额外的交易时间：
            if now.hour == 23 and now.minute < 5:  # 每天 23:05 额外触发
                await wait_until(23, 5)
            elif is_saturday and now.hour in [7, 8]:  # 星期六 7:00 和 8:00 跳过
                await wait_until(9, 0)  # 跳过到 9:00 执行
            else:
                # 每半个小时唤醒一次
                await wait_until_half_hour()
            
            # 登录并获取 CST 和 X-SECURITY-TOKEN
            cst, security_token = login()

            # 运行交易策略
            #rsi_ema_macd(cst, security_token)
            #ema_trend(cst, security_token)
            mta(cst, security_token)
        
            print(f"⏳ 等待执行第{trade_count + 1}次交易")
            trade_count += 1

        except KeyboardInterrupt:
            print("\n🛑 交易中断，退出程序")
            break
'''         
async def run_trading():
    # 初始化交易次数计数器
    while True:
        try:
            cst, security_token = login()

            # 获取当前时间
            now = datetime.now()

            # 计算当前时间到下一个 5 分钟的03秒时刻的时间差
            next_run_time = (now + datetime.timedelta(minutes=5)).replace(second=3, microsecond=0)
            
            # 如果当前时间已经是目标时刻（例如 16:10:03），则不需要等待
            if now.minute % 5 == 0 and now.second == 3:
                time_to_wait = 0
            else:
                # 如果当前时间已经过了目标时间（比如现在是 16:10:05），则计算下一个目标时间
                if now.second > 3:
                    next_run_time += datetime.timedelta(minutes=5)
                time_to_wait = (next_run_time - now).total_seconds()

            # 等待直到下一个目标时刻（每5分钟的03秒）
            await asyncio.sleep(time_to_wait)

            # 执行交易
            mta(cst, security_token)

            # 进入每5分钟的03秒执行一次的循环
            while True:
                # 每次执行交易后，等待 300 秒（5 分钟）
                await asyncio.sleep(300)  # 等待 5 分钟

                # 执行交易
                mta(cst, security_token)

        except KeyboardInterrupt:
            break
            
if __name__ == "__main__":
    try:
        # 在新线程中运行 Flask 服务器
        flask_thread = Thread(target=run_server)
        flask_thread.daemon = True  # 使 Flask 线程在主线程退出时自动结束
        flask_thread.start()

        # 启动交易（确保异步运行）
        asyncio.run(run_trading())

    except KeyboardInterrupt:
        print("\n🛑 主程序被手动中断，退出程序")
