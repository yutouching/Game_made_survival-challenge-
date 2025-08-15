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
    "S": 0,  # ← 新增社交值
}

# 📌 游戏主入口
label start:
    scene bg room
    with fade

    "欢迎进入原型系统测试。"
    
    # 初始化课程系统
    $ initialize_courses(player_major)
    
    $ player["e"] = calc_max_e(player["H"])
    jump game_loop


# 📌 专业选择
label choose_major:
    "请选择你的专业："
    menu:
        "计算机科学":
            $ player_major = "computer_science"
            $ initialize_courses(player_major)
        "数学专业":
            $ player_major = "mathematics" 
            $ initialize_courses(player_major)
        "物理专业":
            $ player_major = "physics"
            $ initialize_courses(player_major)
    
    "你选择了[majors[player_major]['name']]专业。"
    return

# 📌 每日主循环
label game_loop:
    # 检查是否需要推进天数（处理跨天熬夜）
    python:
        if player["current_hour"] >= 24:
            # 跨天了，推进天数
            extra_days = player["current_hour"] // 24
            player["days"] += extra_days
            player["current_hour"] = player["current_hour"] % 24
            # 确保新的一天至少从7点开始
            if player["current_hour"] < 7:
                player["current_hour"] = 7
    
    python:
        display_day, display_hour, time_str = format_time_display(player["current_hour"], player["days"])
    
    "[time_str] - 当前状态：[player['state']]，健康：[player['H']]，精力：[player['e']]，心情：[player['m']]"

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

    # 检查是否因为熬夜而起床困难
    if player.get("last_overtime_hours", 0) > 0:
        $ overtime_hours = player["last_overtime_hours"]
        $ risk, is_oversleep, oversleep_hours = calculate_oversleep_risk(player, overtime_hours)
        
        if is_oversleep:
            "昨晚熬夜的后果显现了......"
            "你感到异常困倦，根本起不来床！"
            $ oversleep_msg = apply_oversleep_penalty(player, oversleep_hours)
            "[oversleep_msg]"
        else:
            "虽然昨晚熬夜了，但你还是准时起床了。"
        
        # 清除熬夜记录
        $ player["last_overtime_hours"] = 0

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
            jump behavior_precheck
        "社交 2 小时":
            $ player["selected_behavior"] = "social_2h"
            jump behavior_precheck
        "家务 1 小时":
            $ player["selected_behavior"] = "chores_1h"
            jump behavior_precheck
        "打游戏 2 小时":
            $ player["selected_behavior"] = "play_game_2h"
            jump behavior_precheck
        "小憩 1 小时":
            $ player["selected_behavior"] = "nap_1h"
            jump behavior_precheck
        "结束今日":
            jump daily_end

# 📌 学习子菜单
label study_menu:
    "选择学习时长："
    menu:
        "学习 2 小时":
            $ player["study_hours"] = 2
            jump choose_course
        "学习 4 小时":
            $ player["study_hours"] = 4
            jump choose_course
        "学习 6 小时":
            $ player["study_hours"] = 6
            jump choose_course
        "返回":
            jump daily_decision

# 📌 课程选择菜单
label choose_course:
    "选择要学习的课程："
    menu:
        "高等数学 I (当前阶段: [get_course_stage('advanced_math')])":
            $ player["selected_course"] = "advanced_math"
            jump study_course
        "概率统计 (当前阶段: [get_course_stage('probability')])":
            $ player["selected_course"] = "probability"
            jump study_course
        "大学物理 I (当前阶段: [get_course_stage('physics')])":
            $ player["selected_course"] = "physics"
            jump study_course
        "大学化学 (当前阶段: [get_course_stage('chemistry')])":
            $ player["selected_course"] = "chemistry"
            jump study_course
        "线性代数 (当前阶段: [get_course_stage('linear_algebra')])":
            $ player["selected_course"] = "linear_algebra"
            jump study_course
        "返回":
            jump study_menu

# 📌 执行学习课程
label study_course:
    $ course_key = player["selected_course"]
    $ hours = player["study_hours"]
    $ player["selected_behavior"] = f"study_{hours}h"
    
    jump behavior_precheck

# 📌 行为预检查（处理熬夜确认）
label behavior_precheck:
    python:
        can_do, msg = can_perform_behavior(player, player["selected_behavior"])
        
    if not can_do:
        if msg == "extreme_overtime":
            "你熬夜太狠了，昏过去了！"
            $ player["H"] = max(0, player["H"] - 15)
            "健康值下降15点。"
            jump daily_end
        elif msg == "needs_overtime_confirm":
            python:
                duration = get_behavior_duration(player["selected_behavior"])
                end_time = player["current_hour"] + duration
                overtime_hours = end_time - 23
                
                # 计算结束时间显示
                if end_time >= 24:
                    display_end_day = player["days"] + 1
                    display_end_hour = end_time - 24
                    time_desc = f"第{display_end_day}天 {display_end_hour}:00"
                else:
                    time_desc = f"今天 {end_time}:00"
            
            "这个行动会让你熬夜到[time_desc]（熬夜 [overtime_hours] 小时），确定要继续吗？"
            menu:
                "确定，我要熬夜":
                    jump behavior_executor
                "算了，换个别的":
                    jump daily_decision
        else:
            # 其他错误消息（如精力不足等）
            "[msg]"
            jump daily_decision
    else:
        # 可以正常执行
        jump behavior_executor

# 📌 行为执行
label behavior_executor:
    # 检查是否为学习行为
    if "study_" in player["selected_behavior"]:
        jump study_execution
    else:
        # 普通行为执行
        if player["selected_behavior"] == "exercise_1h":
            "你去运动了 1 小时。"
        elif player["selected_behavior"] == "play_game_2h":
            "你玩了 2 小时游戏。"
        elif player["selected_behavior"] == "social_2h":
            "你进行了一次社交活动。"
        elif player["selected_behavior"] == "chores_1h":
            "你做了 1 小时家务。"
        elif player["selected_behavior"] == "nap_1h":
            "你小憩了 1 小时。"
        elif player["selected_behavior"] == "seek_treatment":
            "你去看病了。"

        $ result = perform_behavior(player["selected_behavior"], player)
        "[result]"
        jump post_action

# 📌 学习行为执行
label study_execution:
    python:
        course_key = player.get("selected_course", "advanced_math")
        hours = player.get("study_hours", 2)
        course_name = course_definitions[course_key]["name"]
        current_stage = get_course_stage(course_key)
        
    "你开始学习《[course_name]》[hours]小时。"
    "当前阶段：[current_stage]"
    
    # 执行学习行为的状态消耗
    $ behavior_result = perform_behavior(player["selected_behavior"], player)
    "[behavior_result]"
    
    # 更新课程进度（新的掷骰子系统）
    $ progress_result = study_course_with_points(course_key, hours, player)
    "[progress_result]"
    
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
    
    # 重置到第二天早上7点
    $ player["current_hour"] = 7
    $ player["days"] += 1
    
    jump game_loop

# 📌 专业课程配置系统
default majors = {
    "computer_science": {
        "name": "计算机科学",
        "courses": ["advanced_math", "probability", "physics", "chemistry", "linear_algebra"]
    },
    "mathematics": {
        "name": "数学专业", 
        "courses": ["advanced_math", "probability", "linear_algebra", "real_analysis", "abstract_algebra"]
    },
    "physics": {
        "name": "物理专业",
        "courses": ["advanced_math", "physics", "linear_algebra", "theoretical_mechanics", "electromagnetism"]
    }
}

# 📌 课程定义（方便编辑）
default course_definitions = {
    "advanced_math": {
        "name": "高等数学 I",
        "stages": {
            "preview": {"name": "预习", "min_points": 0, "max_points": 150},
            "practice": {"name": "刷题", "min_points": 151, "max_points": 250},
            "summary": {"name": "总结", "min_points": 251, "max_points": 350},
            "completed": {"name": "复习完成", "min_points": 351, "max_points": 999}
        },
        "difficulty": 1.2
    },
    "probability": {
        "name": "概率统计",
        "stages": {
            "preview": {"name": "预习", "min_points": 0, "max_points": 120},
            "practice": {"name": "刷题", "min_points": 121, "max_points": 220},
            "summary": {"name": "总结", "min_points": 221, "max_points": 300},
            "completed": {"name": "复习完成", "min_points": 301, "max_points": 999}
        },
        "difficulty": 1.1
    },
    "physics": {
        "name": "大学物理 I",
        "stages": {
            "preview": {"name": "预习", "min_points": 0, "max_points": 160},
            "practice": {"name": "刷题", "min_points": 161, "max_points": 280},
            "summary": {"name": "总结", "min_points": 281, "max_points": 380},
            "completed": {"name": "复习完成", "min_points": 381, "max_points": 999}
        },
        "difficulty": 1.3
    },
    "chemistry": {
        "name": "大学化学",
        "stages": {
            "preview": {"name": "预习", "min_points": 0, "max_points": 140},
            "practice": {"name": "刷题", "min_points": 141, "max_points": 240},
            "summary": {"name": "总结", "min_points": 241, "max_points": 320},
            "completed": {"name": "复习完成", "min_points": 321, "max_points": 999}
        },
        "difficulty": 1.0
    },
    "linear_algebra": {
        "name": "线性代数",
        "stages": {
            "preview": {"name": "预习", "min_points": 0, "max_points": 130},
            "practice": {"name": "刷题", "min_points": 131, "max_points": 230},
            "summary": {"name": "总结", "min_points": 231, "max_points": 310},
            "completed": {"name": "复习完成", "min_points": 311, "max_points": 999}
        },
        "difficulty": 1.1
    }
}

# 📌 玩家选择的专业和课程进度
default player_major = "computer_science"  # 默认专业，可在游戏开始时选择
default course_progress = {}  # 存储每门课的学习点数

# 📌 初始化课程进度
init python:
    def initialize_courses(major_key):
        """根据专业初始化课程进度"""
        global course_progress
        course_progress = {}
        if major_key in majors:
            for course_id in majors[major_key]["courses"]:
                course_progress[course_id] = 0
    
    def get_course_stage(course_id):
        """获取课程当前阶段"""
        if course_id not in course_progress or course_id not in course_definitions:
            return "未知"
        
        points = course_progress[course_id]
        stages = course_definitions[course_id]["stages"]
        
        for stage_id, stage_data in stages.items():
            if stage_data["min_points"] <= points <= stage_data["max_points"]:
                return stage_data["name"]
        
        return "复习完成"
    
    def add_study_points(course_id, points):
        """添加学习点数并检查是否完成阶段"""
        if course_id not in course_progress:
            course_progress[course_id] = 0
        
        old_stage = get_course_stage(course_id)
        course_progress[course_id] += points
        new_stage = get_course_stage(course_id)
        
        # 检查是否达到复习完成
        if old_stage != "复习完成" and new_stage == "复习完成":
            course_name = course_definitions[course_id]["name"]
            renpy.call_screen("completion_notification", course_name)
        
        return f"获得 {points} 学习点数，当前阶段：{new_stage}"

    # 📌 复习进度面板
screen review_progress_panel():
    modal True
    zorder 200
    
    # 背景遮罩
    add "#000000aa"
    
    # 主面板
    frame:
        xalign 0.5
        yalign 0.5
        xsize 800
        ysize 600
        padding (30, 30)
        background "#001122"
        
        vbox:
            spacing 25
            
            # 标题
            text "复习进度" size 40 color "#ffffff" xalign 0.5 bold True
            
            # 专业信息
            text "专业：[majors[player_major]['name']]" size 28 color "#66c1e0" xalign 0.5
            
            # 课程列表
            viewport:
                ysize 400
                mousewheel True
                
                if len(majors[player_major]["courses"]) > 5:
                    scrollbars "vertical"
                
                vbox:
                    spacing 15
                    
                    for course_id in majors[player_major]["courses"]:
                        if course_id in course_definitions:
                            python:
                                course_name = course_definitions[course_id]["name"]
                                stage = get_course_stage(course_id)
                                points = course_progress.get(course_id, 0)
                                bg_color = "#006633" if stage == "复习完成" else "#003366"
                                stage_color = "#00ff88" if stage == "复习完成" else "#ffcc66"
                            
                            frame:
                                padding (20, 15)
                                background bg_color
                                
                                hbox:
                                    spacing 20
                                    
                                    # 课程名称
                                    text "[course_name]" size 30 color "#ffffff" xsize 300
                                    
                                    # 当前阶段
                                    text "[stage]" size 26 color stage_color
                                    
                                    # 完成标记
                                    if stage == "复习完成":
                                        text "✓" size 32 color "#00ff00" bold True
            
            # 关闭按钮
            textbutton "关闭" action Hide("review_progress_panel") xalign 0.5 text_size 30 xsize 150 ysize 50

# 📌 完成提示框
screen completion_notification(course_name):
    modal True
    zorder 300
    
    add "#000000cc"
    
    frame:
        xalign 0.5
        yalign 0.5
        xsize 500
        ysize 300
        padding (30, 30)
        background "#006633"
        
        vbox:
            spacing 20
            xalign 0.5
            yalign 0.5
            
            text "🎉 恭喜！" size 36 color "#ffffff" xalign 0.5 bold True
            text "[course_name]" size 32 color "#ffff88" xalign 0.5 bold True
            text "已经复习完了！" size 32 color "#ffffff" xalign 0.5 bold True
            
            textbutton "确定" action Hide("completion_notification") xalign 0.5 text_size 28 xsize 120 ysize 50