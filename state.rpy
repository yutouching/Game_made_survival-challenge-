
# 📦 =============================
# 📘 state.rpy - 玩家状态与状态修正管理
# 包含状态倍率表、状态演化逻辑、死亡判定等。
# ===============================

init python:

    # =====================
    # 📌 状态倍率表（行为惩罚/加成）
    # =====================
    status_effects = {
        "正常": {"e": 1.0, "m": 1.0},
        "生病": {"e": 1.2, "m": 1.0},
        "抑郁": {
            "e": 1.0,
            "m": 1.2,
            "gain": 0.8,
            "mood_recovery": 40
        },
        "运动健将": {"e": 0.8, "m": 1.0},
        "作息混乱": {
            "e": 1.0,
            "m": 1.0,
            "gain": 0.9,
            "sickness_bonus": 0.1
        },
        "死亡": {
            "e": 0.0,
            "m": 0.0,
            "gain": 0.0
        }
    }

    # =====================
    # 📌 获取倍率
    # 被 function.rpy → modified_sickness_chance 引用
    # =====================
    def get_active_multipliers(state_name):
        return status_effects.get(state_name, {"e": 1.0, "m": 1.0})

    # =====================
    # 📌 状态变化主判定函数
    # 被 script.rpy → post_action 引用
    # =====================
    def check_state_trigger(player):
        """
        每日行为后触发的状态演化与死亡检测。
        返回：需要展示的状态变化信息（或 None）
        """
        messages = []

        # ===== 健康耗尽直接死亡 =====
        if player["H"] < 1:
            player["state"] = "死亡"
            return "你健康透支，已经死亡。"

        # ===== 作息混乱判定（连续熬夜或过度） =====
        if (
            player.get("consecutive_night", 0) >= 3 or
            player.get("total_night", 0) / max(1, player.get("days", 1)) > 2/3
        ):
            player["consecutive_night"] = 0
            player["state"] = "作息混乱"
            messages.append("你长期熬夜，作息完全紊乱了。")

        # ===== 作息混乱 → 生病 =====
        if player["state"] == "作息混乱":
            p = modified_sickness_chance(player)
            if roll_event_chance(p):
                player["state"] = "生病"
                messages.append(f"你的作息紊乱引发身体问题，生病了。（概率 {p:.0%}）")

        # ===== 心情低落 → 抑郁 =====
        if player["m"] < 20:
            player["low_m_days"] = player.get("low_m_days", 0) + 1
        else:
            player["low_m_days"] = 0

        if player["low_m_days"] >= 3 and player["state"] not in ["抑郁", "死亡"]:
            base_p = 0.7
            s = min(player.get("S", 0), 5)
            final_p = round(base_p * (1 - 0.1 * s), 3)

            if roll_event_chance(final_p):
                player["state"] = "抑郁"
                messages.append(f"你长期心情低落，陷入了抑郁状态。（概率 {final_p:.0%}）")

        # ===== 生病/抑郁 → 重病/重度抑郁 → 死亡 =====
        if player["state"] in ["生病", "抑郁"]:
            player["state_days"] = player.get("state_days", 0) + 1

            if player["state_days"] == 7:
                severe = "重病" if player["state"] == "生病" else "重度抑郁"
                player["severe_state"] = severe
                player["severe_days"] = 1
                messages.append(f"你的情况恶化，进入了{severe}状态。")

            elif player.get("severe_state") in ["重病", "重度抑郁"]:
                player["severe_days"] += 1
                chance = death_chance_by_severe_days(player["severe_days"])
                if roll_event_chance(chance):
                    player["state"] = "死亡"
                    return f"你在 {player['severe_state']} 中失去了生命。"

        else:
            # 其他状态时清空计数器
            player["state_days"] = 0
            player["severe_days"] = 0
            player["severe_state"] = None

        return "\n".join(messages) if messages else None
