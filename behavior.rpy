# 📦 =============================
# 📘 behavior.rpy - 玩家行为执行模块
# 按功能分区：基础配置 → 行为系统 → 学习系统 → 治疗系统 → 熬夜系统
# 
# 🔧 基础配置区：行为定义表、耗时表、持续时间获取
# 🎯 通用行为系统：行为合法性检查、执行、状态消耗
# 📚 学习系统：课程学习、掷骰子系统、进度推进、完成检查
# 🏥 治疗系统：轻度治疗、重病治疗、连续治疗流程管理
# 🌙 熬夜系统：时间检查、健康惩罚分级、极限熬夜处理
# 
# 所有行为都通过 behavior_precheck 进行预检查，确保合法性
# 支持熬夜确认、极限熬夜自动昏倒、健康惩罚分级
# =============================

init python:
    import random
    import math

    # ==========================================
    # � 【基础配置区】行为定义表与配置
    # ==========================================
    
    # 📌 行为耗时定义表（单位：小时）
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

    # 📌 行为消耗定义表（e/m 单位）
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

    # ==========================================
    # 🎯 【通用行为系统】执行、合法性检查、状态消耗
    # ==========================================
    
    # 📌 行为合法性检查 - 被 script.rpy 调用前验证行为是否可执行
    def can_perform_behavior(player, behavior_key, allow_overtime=False):
        duration = get_behavior_duration(behavior_key)
        current_time = player.get("current_hour", 7)
        end_time = current_time + duration

        # 检查是否会超过上限（34小时，即第二天早上10点）
        if end_time > 34:
            return False, "extreme_overtime"  # 特殊标记，表示会昏倒

        # 检查是否会熬夜（超过23点）
        if end_time > 23 and not allow_overtime:
            return False, "needs_overtime_confirm"  # 特殊标记，需要确认熬夜
        
        # 检查精力和心情
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

    # 📌 行为执行函数 - 包括状态检查、耗时推进、e/m 消耗，含特殊行为判断
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

        # ✅ 执行行为（已通过预检查，直接执行）
        duration = get_behavior_duration(behavior_key)
        
        # 更新当前时间
        old_hour = player["current_hour"]
        player["current_hour"] += duration
        
        # 检查是否熬夜并应用健康惩罚
        overtime_msg = apply_overtime_penalty(player, old_hour, player["current_hour"])

        result = apply_behavior_cost(player, behavior_key)
        
        if overtime_msg:
            return f"{result}\n{overtime_msg}"
        else:
            return result

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

    # ==========================================
    # � 【学习系统】课程学习、掷骰子系统、进度推进
    # ==========================================
    
    def study_course_with_points(course_id, hours, player):
        """学习指定课程并获得点数 - 基于掷骰子系统"""
        if course_id not in course_definitions:
            return "课程不存在"
        
        if hours not in [2, 4, 6]:
            return "无效学习时长"
        
        # 基础掷骰：d100 + d20
        base_roll = random.randint(1, 100) + random.randint(1, 20)
        
        # 健康修正
        health_modifier = 0
        if player["H"] > 80:
            health_modifier = random.randint(1, 20)
        elif player["H"] < 30:
            health_modifier = -random.randint(1, 20)
        
        # 心情修正
        mood_modifier = 0
        if player["m"] > 80:
            mood_modifier = random.randint(1, 20)
        elif player["m"] < 30:
            mood_modifier = -random.randint(1, 20)
        
        # 学习时长修正
        time_modifier = 0
        if hours == 2:
            time_modifier = -random.randint(1, 10)
        elif hours == 4:
            time_modifier = random.randint(1, 5)
        elif hours == 6:
            time_modifier = random.randint(1, 10)
        
        # 计算最终结果
        final_roll = base_roll + health_modifier + mood_modifier + time_modifier
        
        # 判定成果等级
        if final_roll <= 5:
            result_type = "大失败"
            study_points = 0
        elif 6 <= final_roll <= 50:
            result_type = "失败"
            study_points = min(70, final_roll // 2)
        elif 51 <= final_roll <= 95:
            result_type = "成功"
            study_points = min(70, final_roll // 2)
        else:  # >= 96
            result_type = "大成功"
            study_points = min(70, final_roll // 2)
        
        # 添加学习点数
        if course_id not in course_progress:
            course_progress[course_id] = 0
        
        old_stage = get_course_stage(course_id)
        course_progress[course_id] += study_points
        new_stage = get_course_stage(course_id)
        
        # 检查是否达到复习完成
        if old_stage != "复习完成" and new_stage == "复习完成":
            course_name = course_definitions[course_id]["name"]
            renpy.show_screen("completion_notification", course_name)
        
        # 构建详细结果信息
        course_name = course_definitions[course_id]["name"]
        roll_details = f"基础骰子: {base_roll}"
        if health_modifier != 0:
            roll_details += f", 健康修正: {health_modifier:+d}"
        if mood_modifier != 0:
            roll_details += f", 心情修正: {mood_modifier:+d}"
        if time_modifier != 0:
            roll_details += f", 时长修正: {time_modifier:+d}"
        
        result_msg = f"学习《{course_name}》{hours}小时\n"
        result_msg += f"{roll_details}\n"
        result_msg += f"总点数: {final_roll} → {result_type}！\n"
        result_msg += f"获得学习点数: {study_points}, 当前阶段: {new_stage}"
        
        return result_msg

    # ==========================================
    # 🏥 【治疗系统】轻度治疗、重病治疗、连续治疗流程
    # ==========================================
    
    # 📌 轻度看病函数
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

    # 📌 触发治疗流程前的提示（由 script 中调用）
    def prompt_start_recovery(player):
        # 在 script.rpy 中调用此函数后给出菜单
        player["recovery_in_progress"] = player["state"]
        player["recovery_days"] = 1
        player["force_skip_day"] = True

    # 📌 检查连续治疗是否成功（每日结束调用）
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

    # ==========================================
    # 🌙 【熬夜系统】时间检查、健康惩罚、极限熬夜处理
    # ==========================================
    
    # 📌 熬夜惩罚系统
    def apply_overtime_penalty(player, start_hour, end_hour):
        """应用熬夜健康惩罚并记录熬夜信息"""
        if end_hour <= 23:
            return None  # 没有熬夜
        
        # 计算熬夜时长
        overtime_hours = end_hour - 23
        
        # 记录熬夜信息供明天起床检查使用
        player["last_overtime_hours"] = overtime_hours
        
        # 计算健康损失
        health_loss = 0
        overtime_msg = ""
        
        if overtime_hours <= 4:
            # 前4小时，每小时-5健康
            health_loss = overtime_hours * 5
            overtime_msg = f"你今天熬夜了 {overtime_hours} 小时"
        else:
            # 前4小时 + 超过4小时的部分每小时-7健康
            health_loss = 4 * 5 + (overtime_hours - 4) * 7
            overtime_msg = f"你今天熬夜了 {overtime_hours} 小时，严重透支"
        
        # 应用健康损失
        player["H"] = max(0, player["H"] - health_loss)
        overtime_msg += f"，健康值下降 {health_loss}"
        
        return overtime_msg
    
    def check_extreme_overtime(player, behavior_key):
        """检查是否会导致极度熬夜（昏倒）"""
        duration = get_behavior_duration(behavior_key)
        end_time = player["current_hour"] + duration
        
        if end_time > 34:
            return True, end_time
        return False, end_time

    # 📌 熬夜起床困难系统（集中于此）
    # 可调配置：完全独立于学习系统
    oversleep_settings = {
        # 基础风险骰：d100
        "base_risk_dice": 100,
        # 每小时熬夜附加骰：d10 × 熬夜小时数
        "per_hour_dice": 10,
        # 修正骰：健康/心情优秀时的减免；差时的惩罚
        "health_good_bonus_dice": 20,   # 健康 > 80 → -d20
        "health_low_penalty_dice": 20,  # 健康 < 30 → +d20
        "mood_good_bonus_dice": 20,     # 心情 > 80 → -d20
        "mood_low_penalty_dice": 20,    # 心情 < 30 → +d20
        # 失败阈值：风险 > 阈值 → 起床失败
        "risk_threshold": 50,
    }

    def _d(sides):
        return random.randint(1, sides)

    def calculate_oversleep_risk(player, overtime_hours):
        """
        返回: (risk_value:int, is_oversleep:bool, oversleep_hours:int)
        风险 = d100 + 熬夜小时 × d10 - (H>80)d20 + (H<30)d20 - (m>80)d20 + (m<30)d20
        晚起时长 = ceil(risk/10 - 5)
        """
        cfg = oversleep_settings
        risk = _d(cfg["base_risk_dice"]) + overtime_hours * _d(cfg["per_hour_dice"])

        if player.get("H", 0) > 80:
            risk -= _d(cfg["health_good_bonus_dice"])
        if player.get("H", 0) < 30:
            risk += _d(cfg["health_low_penalty_dice"])
        if player.get("m", 0) > 80:
            risk -= _d(cfg["mood_good_bonus_dice"])
        if player.get("m", 0) < 30:
            risk += _d(cfg["mood_low_penalty_dice"])

        is_oversleep = risk > cfg["risk_threshold"]
        oversleep_hours = max(1, math.ceil(risk / 10.0 - 5)) if is_oversleep else 0
        return risk, is_oversleep, oversleep_hours

    def apply_oversleep_penalty(player, oversleep_hours, risk_value=None):
        """应用晚起惩罚：推迟当日开始时间，并返回提示文本。"""
        if oversleep_hours <= 0:
            return "你勉强按时起床了。"
        # 早上7点基础上延后
        player["current_hour"] = min(23, player.get("current_hour", 7) + oversleep_hours)
        # 可按需追加轻微精力/心情惩罚（这里不追加，保持与学习系统完全分离）
        if risk_value is None:
            return f"你晚起了 {oversleep_hours} 小时。"
        else:
            return f"风险={risk_value}，你晚起了 {oversleep_hours} 小时。"

    # ==========================================
    # 🏁 【behavior.rpy 模块结束】
    # ==========================================