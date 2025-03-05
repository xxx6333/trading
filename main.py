from threading import Thread
import asyncio
from datetime import datetime, timedelta
from config import login
from mta import *

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


if __name__ == "__main__":
    try:
        asyncio.run(run_trading())
    except KeyboardInterrupt:
        print("\n🛑 主程序被手动中断，退出程序")
