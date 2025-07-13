# 📘 声明角色
define narrator = Character(None)  # 系统叙述
define p = Character("你")         # 玩家自己

# 📌 玩家初始状态
default player = {
    "days": 1,
    "H": 100,
    "e": 0,
    "m": 100,
    "state": "normal",
    "day_time": 16,
    "current_hour": 7,
    "day_time_blocked": 0,
    "force_skip_day": False,
    "skip_reason": "",
    "selected_behavior": None,
}

# 📌 游戏主入口
label start:
    scene bg room
    with fade

    "欢迎进入原型系统测试。"
    $ player["e"] = calc_max_e(player["H"])
    jump game_loop

# 📌 每日主循环
label game_loop:
    "Day [player['days']] - 当前状态：[player['state']]，健康：[player['H']]，精力：[player['e']]，心情：[player['m']]"

    $ player["day_time_blocked"] = 0

    if player.get("force_skip_day", False):
        "[player.get('skip_reason', '今天被强制跳过。')]"
        $ player["force_skip_day"] = False
        $ player["skip_reason"] = ""
        jump daily_end

    jump start_day

# 📌 开始新的一天
label start_day:
    $ player["day_time"] = 16
    $ player["current_hour"] = 7

    "新的一天开始了。你感到……"

    if player.get("recovery_in_progress") and player.get("selected_behavior") != "seek_treatment":
        $ player["recovery_in_progress"] = None
        $ player["recovery_days"] = 0

    if player["state"] in ["重病", "重度抑郁"] and not player.get("recovery_in_progress"):
        "你当前处于严重状态，需要连续三天治疗才能缓解。"
        "是否今天进行治疗（跳过所有决策）？"
        menu:            
            "开始全天治疗":
                $ player["recovery_in_progress"] = player["state"]
                $ player["recovery_days"] = player.get("recovery_days", 0) + 1
                $ player["day_time_blocked"] = 24
                $ player["force_skip_day"] = True
                $ player["skip_reason"] = "你专注接受了一整天的治疗……"
                jump daily_end
            "继续正常安排":
                "你决定坚持一下，看看能不能扛过去……"

    jump daily_decision

# 📌 每日决策主菜单
label daily_decision:

    if player["current_hour"] >= 23:
        "已经晚上 11 点了，你是否还要继续今天的活动？"
        menu:
            "是，我要熬夜":
                $ player["day_time"] = 4
                jump daily_decision
            "否，结束今日":
                jump daily_end

    if player["state"] in ["severe_sick", "severe_depressed"]:
        "你今天身体状况非常糟糕……"
        menu:
            "跳过今日并就医":
                $ player["skip_reason"] = "你因为严重状况被送往医院，今天休息了一天。"
                $ player["force_skip_day"] = True
                jump daily_end
            "尝试坚持活动":
                pass
    
    if player["state"] in ["sick", "depressed"]:
        "你有点不舒服，要去看病吗？"
        menu:
            "就医（仅生病/抑郁时可见）": 
                $ player["selected_behavior"] = "seek_treatment"
                jump behavior_executor
            "坚持":
                pass


    "你今天想做什么？"
    menu:
        "学习":
            jump study_menu
        "运动 1 小时":
            $ player["selected_behavior"] = "exercise_1h"
            jump behavior_executor
        "社交 2 小时":
            $ player["selected_behavior"] = "social_2h"
            jump behavior_executor
        "家务 1 小时":
            $ player["selected_behavior"] = "chores_1h"
            jump behavior_executor
        "打游戏 2 小时":
            $ player["selected_behavior"] = "play_game_2h"
            jump behavior_executor
        "小憩 1 小时":
            $ player["selected_behavior"] = "nap_1h"
            jump behavior_executor
        "结束今日":
            jump daily_end

# 📌 学习子菜单
label study_menu:
    "选择学习时长："
    menu:
        "学习 2 小时":
            $ player["selected_behavior"] = "study_2h"
            jump behavior_executor
        "学习 4 小时":
            $ player["selected_behavior"] = "study_4h"
            jump behavior_executor
        "学习 6 小时":
            $ player["selected_behavior"] = "study_6h"
            jump behavior_executor
        "返回":
            jump daily_decision

# 📌 行为执行
label behavior_executor:
    $ perform_behavior(player["selected_behavior"], player)
    jump post_action

# 📌 行为后处理
label post_action:
    $ state_msg = check_state_trigger(player)
    if state_msg:
        "[state_msg]"
    jump behavior_event_check  # 若你接入了统一事件入口
    # jump daily_decision  # 如果未集成事件系统，取消上行用这行

# 📌 每日结束
label daily_end:
    "你的一天结束了。"
    $ player["days"] += 1
    jump game_loop
