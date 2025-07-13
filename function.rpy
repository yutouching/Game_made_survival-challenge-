
# 📦 =============================
# 📘 function.rpy - 游戏通用逻辑函数定义
# 本文件包含效率计算、状态判定、事件触发等后端逻辑。
# ===============================

init python:
    import math
    import random

    # =====================
    # 📌 效率 & 精力相关函数
    # =====================

    def get_efficiency(e, m, max_e=100, max_m=100):
        """
        引用于行为系统（如学习行为）。
        根据精力值 e 与心情值 m 计算学习效率百分比。
        返回值范围为 0.0 ~ 1.0
        """
        return ((e / max_e) + (m / max_m)) / 2

    def calc_max_e(H):
        """
        用于初始状态和每日精力刷新。
        根据健康值 H 计算精力上限。
        函数：sqrt(H) × 40，对应 H = 1~6 → e = 40 ~ 100
        """
        return round(math.sqrt(H) * 40)

    # =====================
    # 📌 生病概率函数
    # =====================

    def sickness_chance(H, H_max=6, base_chance=0.4, min_chance=0.03, curve=2):
        """
        基础生病概率：健康值越低，风险越高。
        使用凸形函数调整生病风险。
        引用于作息混乱判定。
        """
        ratio = 1 - (H / H_max)
        risk_factor = ratio ** curve
        return round(min_chance + (base_chance - min_chance) * risk_factor, 3)

    def modified_sickness_chance(player, H_max=6):
        """
        综合考虑状态修正的生病概率。
        包括 health 系数和 state 中的 sickness_bonus。
        依赖函数：get_active_multipliers(state_name) 来自 state.rpy
        """
        base = sickness_chance(player["H"], H_max)
        multipliers = get_active_multipliers(player.get("state", "正常"))
        bonus = multipliers.get("sickness_bonus", 0.0)
        return min(1.0, round(base + bonus, 3))

    # =====================
    # 📌 熬夜相关函数
    # =====================

    def late_trigger_probability(sleep_hours):
        """
        睡眠不足 → 晚起概率提升。
        用于夜间结束后计算是否“晚起”。
        """
        lack = max(0, 8 - sleep_hours)
        if lack == 0: return 0.05
        elif lack == 1: return 0.2
        elif lack == 2: return 0.4
        elif lack == 3: return 0.6
        else: return 0.8

    def late_sleep_delay(sleep_hours):
        """
        根据缺觉小时数决定晚起延迟时间（小时）。
        使用正态分布（均值=缺觉，σ=0.7）模拟。
        """
        mu = max(0, 8 - sleep_hours)
        sigma = 0.7
        delay = random.gauss(mu, sigma)
        return max(1, round(delay))

    # =====================
    # 📌 通用事件概率函数
    # =====================

    def roll_event_chance(p):
        """
        用于判断事件是否触发。p 是 [0, 1] 区间的概率。
        用于状态触发、社交事件等。
        """
        return random.random() < p

    # =====================
    # 📌 社交类事件触发概率
    # =====================

    def get_social_bonus_chance(S):
        """
        根据社交值返回 passive event 的触发概率。
        用于 maybe_trigger_social_event 等事件触发逻辑。
        """
        if S < 2:
            return 0.1
        elif S < 4:
            return 0.2
        elif S < 5:
            return 0.3
        else:
            return 0.5  # 社交达人阶段最大触发概率

    # =====================
    # 📌 重病 / 重度抑郁 死亡概率增长
    # =====================

    def death_chance_by_severe_days(severe_days, base=0.05, growth=0.05, max_p=0.9):
        """
        进入“重病”或“重度抑郁”后的每日死亡概率。
        每天递增，最多不超过 max_p。
        第一天 base，之后每 +1 天增加 growth。
        """
        chance = base + growth * (severe_days - 1)
        return min(round(chance, 3), max_p)

    # =====================
    # 📌 跳过整天（重病、强制休息等）
    # =====================

    def skip_whole_day(player, reason="你决定跳过今天的安排。"):
        """
        设置玩家状态为跳过当日。
        引用于 script.rpy → game_loop/daily_end 跳转。
        """
        player["force_skip_day"] = True
        player["skip_reason"] = reason
