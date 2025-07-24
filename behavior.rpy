
# 📦 =============================
# 📘 behavior.rpy - 玩家行为执行模块
# 包含行为定义、合法性判断、状态消耗、治疗流程、状态推进
# =============================

init python:

    # =====================
    # 📌 行为耗时定义表（单位：小时）
    # =====================
    behavior_duration_table = {
        "study_2h": 2,
        "study_4h": 4,
        "study_6h": 6,
        "exercise_1h": 1,
        "play_game_2h": 2,
        "social_2h": 2,
        "nap_1h": 1,
        "chores_1h": 1,
        "seek_treatment": 6,  # 用于轻度生病/抑郁的看病行为
    }

    def get_behavior_duration(behavior_key):
        return behavior_duration_table.get(behavior_key, 0)

    # =====================
    # 📌 行为消耗定义表（e/m 单位）
    # =====================
    behavior_table = {
        "study_2h": {"e": 20, "m": 20},
        "study_4h": {"e": 40, "m": 40},
        "study_6h": {"e": 60, "m": 60},
        "exercise_1h": {"e": 20, "m": -10},
        "play_game_2h": {"e": 10, "m": -20},
        "social_2h": {"e": 20, "m": -20},
        "nap_1h": {"e": -10, "m": -5},
        "chores_1h": {"e": 15, "m": 0},
        "seek_treatment": {"e": 30, "m": 30},
    }

    # =====================
    # 📌 行为合法性检查
    # 被 script.rpy 调用前验证行为是否可执行
    # =====================
    def can_perform_behavior(player, behavior_key, allow_overtime=False):
        duration = get_behavior_duration(behavior_key)
        current_time = player.get("day_time_blocked", 0)

        if not allow_overtime and current_time + duration > 16:
            return False, "马上要睡觉了，做点别的吧。"

        behavior = behavior_table.get(behavior_key)
        if not behavior:
            return False, "未知行为"

        multipliers = get_active_multipliers(player.get("state", "正常"))
        e_cost = round(behavior["e"] * multipliers.get("e", 1.0), 2)
        m_cost = round(behavior["m"] * multipliers.get("m", 1.0), 2)

        if player["e"] < e_cost:
            return False, f"你没有精力完成这件事（需要: {e_cost}）"
        if player["m"] < m_cost:
            return False, f"你现在没有心情（需要: {m_cost}）"

        return True, ""

    # =====================
    # 📌 行为执行函数
    # 包括状态检查、耗时推进、e/m 消耗，含特殊行为判断
    # =====================
    def perform_behavior(behavior_key, player):
        # 🛑 若处于重病/重度抑郁阶段且尝试使用 seek_treatment，看病无效
        if player.get("recovery_in_progress") and behavior_key == "seek_treatment":
            return "简单看看医生对你的情况已经没有帮助，你需要更深入的治疗。"

        # 🩺 轻度状态时的“看病”行为
        if behavior_key == "seek_treatment":
            if player["state"] == "生病":
                return heal_physical(player)
            elif player["state"] == "抑郁":
                return heal_mental(player)
            else:
                return "你当前没有需要治疗的症状。"

        # ✅ 常规行为合法性判断
        can_do, msg = can_perform_behavior(player, behavior_key)
        if not can_do:
            return msg

        duration = get_behavior_duration(behavior_key)
        player["day_time_blocked"] += duration
        player["current_hour"] += duration

        return apply_behavior_cost(player, behavior_key)

    def apply_behavior_cost(player, behavior_key):
        behavior = behavior_table.get(behavior_key)
        if not behavior:
            return "行为不存在"

        multipliers = get_active_multipliers(player.get("state", "正常"))
        e_cost = round(behavior["e"] * multipliers.get("e", 1.0), 2)
        m_cost = round(behavior["m"] * multipliers.get("m", 1.0), 2)

        player["e"] -= e_cost
        player["m"] -= m_cost

        return f"{behavior_key} 执行：精力 -{e_cost}, 心情 -{m_cost}"

    # =====================
    # 📌 学习课程推进（用于具体课程系统）
    # =====================
    def study_specific_course(course, hours, player):
        bl_table = {2: 0.05, 4: 0.08, 6: 0.12}
        if hours not in bl_table:
            return "无效学习时长"

        bl = bl_table[hours]
        eff = get_efficiency(player["e"], player["m"])
        gain = round(bl * eff, 3)

        multipliers = get_active_multipliers(player.get("state", "正常"))
        gain *= multipliers.get("gain", 1.0)

        remain = 1.0 - course["progress"]
        actual_gain = min(gain, remain)
        course["progress"] += actual_gain

        return f"学习《{course['name']}》{hours}小时，进度提升 {actual_gain:.3f}"

    # =====================
    # 📌 轻度看病函数
    # =====================
    def heal_physical(player):
        player["e"] = max(player["e"] - 30, 0)
        player["m"] = max(player["m"] - 20, 0)
        player["state"] = "正常"
        player["state_days"] = 0
        return "你前往医院接受了治疗，恢复了健康，但耗费了不少精力。"

    def heal_mental(player):
        player["e"] = max(player["e"] - 20, 0)
        player["m"] = max(player["m"] - 30, 0)
        player["state"] = "正常"
        player["state_days"] = 0
        return "你接受了心理咨询，逐渐走出了情绪低谷，但也感到疲惫。"

    # =====================
    # 📌 触发治疗流程前的提示（由 script 中调用）
    # =====================
    def prompt_start_recovery(player):
        # 在 script.rpy 中调用此函数后给出菜单
        player["recovery_in_progress"] = player["state"]
        player["recovery_days"] = 1
        player["force_skip_day"] = True

    # =====================
    # 📌 检查连续治疗是否成功（每日结束调用）
    # =====================
    def check_severe_recovery(player):
        if not player.get("recovery_in_progress"):
            return None

        # ✅ 只有真正跳过整天（非行为处理）才计为一次有效治疗
        if not player.get("force_skip_day", False):
            return None

        player["recovery_days"] += 1
        player["force_skip_day"] = False  # 清除标记

        if player["recovery_days"] >= 3:
            player["state"] = "生病" if player["recovery_in_progress"] == "重病" else "抑郁"
            player["recovery_in_progress"] = None
            player["recovery_days"] = 0
            return "连续三天治疗完成，你的状态有所缓解。"
        else:
            return f"你正在进行第 {player['recovery_days']} 天的治疗。"

