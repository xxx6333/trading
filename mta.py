import requests
import pandas as pd
import numpy as np
import time
from config import *

# 全局配置
EPIC = "XRPUSD"        # 交易品种
RESOLUTION = "MINUTE_30"    # 交易周期
ATR_PERIOD = 14        # ATR周期
STOP_MULTIPLIER = 1.5  # 止损倍数
LEVERAGE = 2
SPREAD = 0.012

def calculate_indicators(df):
    """计算技术指标"""
    # EMA 计算
    df["ema50"] = df["close"].ewm(span=50, adjust=False).mean()
    df["ema100"] = df["close"].ewm(span=100, adjust=False).mean()

    # MACD 计算 (12, 26, 9)
    df["ema12"] = df["close"].ewm(span=12, adjust=False).mean()
    df["ema26"] = df["close"].ewm(span=26, adjust=False).mean()
    df["macd"] = df["ema12"] - df["ema26"]
    df["signal"] = df["macd"].ewm(span=9, adjust=False).mean()

    # RSI 计算 (14)
    delta = df["close"].diff()
    gain = delta.where(delta > 0, 0)
    loss = -delta.where(delta < 0, 0)
    avg_gain = gain.ewm(alpha=1/14, adjust=False).mean()
    avg_loss = loss.ewm(alpha=1/14, adjust=False).mean()
    rs = avg_gain / avg_loss
    df["rsi"] = 100 - (100 / (1 + rs))

    # ATR 计算 (14)
    df["tr"] = np.maximum(df["high"] - df["low"],
                          np.abs(df["high"] - df["close"].shift(1)),
                          np.abs(df["low"] - df["close"].shift(1)))
    df["atr"] = df["tr"].rolling(ATR_PERIOD).mean()
    df.drop(columns=["tr"], inplace=True)

    return df

def calculate_position_size(current_price, account_balance):
    """计算头寸规模"""
    risk_amount = account_balance * 0.8
    contract_size = (risk_amount / round(current_price, 2)) * LEVERAGE

    return max(1, round(contract_size))  # 最小交易规模为 1

def generate_signal(df):
    """生成交易信号"""
    last_row = df.iloc[-1]
    prev_row = df.iloc[-2]

    long_condition = (
        (last_row["ema50"] > last_row["ema100"]) and  # EMA50 在 EMA100 之上
        (last_row["close"] > last_row["ema50"]) and   # 价格在 EMA50 之上
        (last_row["rsi"] > 45) and                    # RSI 高于 45
        (prev_row["macd"] <= prev_row["signal"]) and 
        (last_row["macd"] > last_row["signal"])       # MACD 金叉
    )

    short_condition = (
        (last_row["ema50"] < last_row["ema100"]) and  # EMA50 在 EMA100 之下
        (last_row["close"] < last_row["ema50"]) and   # 价格在 EMA50 之下
        (last_row["rsi"] < 55) and                    # RSI 低于 55
        (prev_row["macd"] >= prev_row["signal"]) and 
        (last_row["macd"] < last_row["signal"])       # MACD 死叉
    )

    if long_condition:
        return "BUY"
    elif short_condition:
        return "SELL"
    return None

def execute_trade(direction, cst, token, df):
    """执行交易"""
    current_price = df["close"].iloc[-1]
    current_atr = df["atr"].iloc[-1]

    account = get_account_balance(cst, token)
    if not account:
        return

    size = calculate_position_size(current_price, account["balance"])
    if size <= 0:
        return
    
    if direction == "BUY":
        stop_loss = current_price - current_atr * STOP_MULTIPLIER
        initial_tp = current_price + SPREAD + current_atr * STOP_MULTIPLIER * 1.3
    else:
        stop_loss = current_price + SPREAD + current_atr * STOP_MULTIPLIER
        initial_tp = current_price - SPREAD - current_atr * STOP_MULTIPLIER * 1.3

    order = {
        "epic": EPIC,
        "direction": direction,
        "size": size,
        "orderType": "MARKET",
        "stopLevel": round(stop_loss, 3),
        "profitLevel": round(initial_tp, 3),
        "guaranteedStop": False,
        "oco": True
    }

    response = requests.post(
        f"{BASE_URL}positions",
        headers={"CST": cst, "X-SECURITY-TOKEN": token},
        json=order
    )

    if response.status_code == 200:
        print(f"✅ {direction} {size} | 价格: {current_price:.3f} | 止盈: {initial_tp:.3f} | 止损: {stop_loss:.3f}")
    else:
        print(f"❌ 订单失败: {response.status_code} - {response.text}")

def get_positions(cst, token):
    """获取当前持仓"""
    response = requests.get(f"{BASE_URL}positions", headers={
        "CST": cst, "X-SECURITY-TOKEN": token, "Content-Type": "application/json"
    })
    
    if response.status_code == 200:
        return response.json().get("positions", [])
    else:
        print(f"❌ 获取持仓信息失败: {response.text}")
        return []

def mta(cst, token):
    """主策略逻辑"""
    if get_positions(cst, token):
        print("🟡 当前已有持仓，跳过信号检查")
        return

    df = get_market_data(cst, token, EPIC, RESOLUTION)
    if df is None:
        print("❌ K线数据为空，无法计算指标")
        return

    df = calculate_indicators(df)
    if df is None:
        return
    
    # 生成信号
    signal = generate_signal(df)
    if signal:
        execute_trade(signal, cst, token, df)
        
