# 📦 =============================
# 📘 event.rpy - 行为事件系统
# 包含行为触发的自动事件、社交反馈、健康事件等
# =============================

init python:

    # =====================
    # 📌 健康相关：睡眠不足 → 晚起事件
    # =====================
    def check_late_event(player, sleep_hours):
        """
        睡眠不足时，判断是否触发晚起事件，并设置当天封锁时间。
        返回 (是否触发, 消息列表)
        """
        messages = []
        p_trigger = late_trigger_probability(sleep_hours)
        if not roll_event_chance(p_trigger):
            return False, ["你虽然睡得少，但第二天成功起床了。"]

        delay = late_sleep_delay(sleep_hours)
        player["day_time_blocked"] = delay
        messages.append(f"你因为睡眠不足，晚起了 {delay} 小时。")
        return True, messages

    # =====================
    # 📌 社交相关：自动社交事件（行为中）
    # =====================
    def maybe_trigger_passive_social_event(player, behavior_type):
        """
        根据社交值，在行为中自动触发正面/负面事件。
        返回 (事件效果字典, 消息列表)
        """
        p = get_social_bonus_chance(player.get("S", 0))
        if not roll_event_chance(p):
            return {}, []

        if player["S"] >= 3:
            return {"efficiency_bonus": 0.2}, [f"人脉广，{behavior_type}效率提升！"]
        else:
            return {"m_penalty": 10}, [f"社恐影响了你的{behavior_type}表现，心情下降..."]

    # =====================
    # 📌 社交事件：可选聚会邀请
    # =====================
    def maybe_trigger_social_choice_event(player):
        """
        社交值高时，固定概率触发“聚会邀请”事件，返回是否触发+事件结构。
        """
        if player["S"] < 4:
            return False, None
        if not roll_event_chance(0.15):
            return False, None

        return True, {
            "title": "你收到一个同学聚会邀请。",
            "choices": [
                {"label": "去参加", "effect": lambda p: attend_gathering(p)},
                {"label": "不去", "effect": lambda p: decline_gathering(p)}
            ]
        }

    def attend_gathering(player):
        if player["S"] >= 4:
            player["m"] += 15
            return "你在聚会中玩得很开心，心情大幅提升！"
        else:
            player["m"] -= 10
            return "你在聚会中格格不入，感到尴尬..."

    def decline_gathering(player):
        player["m"] -= 5
        return "你拒绝了聚会邀请，稍微有点落寞。"

    # =====================
    # 📌 社交+健康：登山邀请（运动后）
    # =====================
    def maybe_trigger_hiking_event_after_exercise(player):
        """
        运动行为后触发登山事件检测逻辑。
        若满足条件（S > 4 且 20% 概率），返回 True，否则 False。
        """
        if player.get("S", 0) > 4 and roll_event_chance(0.2):
            return True
        return False

# =====================
# 📌 label: 行为后统一事件触发器
# =====================
label behavior_event_check:

    if player["selected_behavior"] == "exercise_1h":
        if maybe_trigger_hiking_event_after_exercise(player):
            jump hiking_event


    elif player["selected_behavior"] == "social_2h":
        $ result, messages = maybe_trigger_passive_social_event(player, "社交")
        python:
            if messages:
                for msg in messages:
                    renpy.say(None, msg)
                if "m_penalty" in result:
                    player["m"] -= result["m_penalty"]

                if "efficiency_bonus" in result:
                    player["bonus_efficiency"] = result["efficiency_bonus"]


    elif player["selected_behavior"] == "play_game_2h":
        if roll_event_chance(0.1):
            "你在游戏中获得了稀有成就，情绪大涨！"
            $ player["m"] += 10


    jump daily_continue


# =====================
# 📌 登山事件 label
# =====================
label hiking_event:

    "你的朋友发来信息，邀请你周末一起去登山。"
    "你要去吗？"
    menu:
        "去":
            if roll_event_chance(player["H"] / 6.0):
                $ player["m"] += 10
                $ player["S"] += 0.2
                "你登山时感觉体能充沛，与朋友也聊得很开心！"
            else:
                $ player["m"] -= 5
                "你在登山途中感到吃力，虽然努力完成了，但有些疲惫。"

        "不去":
            $ player["m"] -= 5
            $ player["S"] -= 0.1
            "你婉拒了邀请，朋友似乎有点失望。"

    jump daily_continue

label daily_continue:
    jump daily_decision
