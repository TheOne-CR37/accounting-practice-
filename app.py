#!/usr/bin/env python3
"""
中级财务会计刷题网页应用
功能：随机刷题、模拟考试、错题本、学习统计
"""
import streamlit as st
import json
import random
import os
import time
from datetime import datetime
from pathlib import Path

# ============================================================
# 页面配置
# ============================================================
st.set_page_config(page_title="中级财务会计刷题", page_icon="📚", layout="wide")

# ============================================================
# 自定义 CSS
# ============================================================
st.markdown("""
<style>
    .question-card {
        background: #f8f9fa;
        border-radius: 12px;
        padding: 24px;
        margin: 16px 0;
        border-left: 4px solid #4A90D9;
    }
    .result-correct {
        background: #d4edda;
        border-radius: 10px;
        padding: 16px;
        border: 1px solid #c3e6cb;
    }
    .result-wrong {
        background: #f8d7da;
        border-radius: 10px;
        padding: 16px;
        border: 1px solid #f5c6cb;
    }
    .info-card {
        background: #e7f3ff;
        border-radius: 10px;
        padding: 16px;
        border: 1px solid #b8daff;
    }
    .sidebar-metric {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        border-radius: 10px;
        padding: 12px;
        color: white;
        text-align: center;
        margin: 8px 0;
    }
    .type-badge {
        display: inline-block;
        padding: 2px 10px;
        border-radius: 12px;
        font-size: 0.85em;
        font-weight: 500;
    }
    .badge-obj { background: #e3f2fd; color: #1565c0; }
    .badge-sub { background: #fff3e0; color: #e65100; }
    .badge-key {
        display: inline-block;
        background: #ff4757;
        color: white;
        padding: 1px 8px;
        border-radius: 10px;
        font-size: 0.75em;
        font-weight: 600;
    }
    .stRadio > div { gap: 6px; }
    .stCheckbox > label { font-size: 1rem; }
</style>
""", unsafe_allow_html=True)

# ============================================================
# 文件路径
# ============================================================
BASE_DIR = Path(__file__).parent
QUESTIONS_FILE = BASE_DIR / "questions.json"
RECORDS_FILE = BASE_DIR / "records.json"

# ============================================================
# 题型映射 & 分值
# ============================================================
TYPE_LABELS = {
    "single_choice": "单选题",
    "multi_choice":  "多选题",
    "true_false":    "判断题",
    "accounting":    "核算题",
}
TYPE_ICONS = {
    "single_choice": "🔘",
    "multi_choice":  "☑️",
    "true_false":    "⚖️",
    "accounting":    "📝",
}
OBJECTIVE_TYPES = {"single_choice", "multi_choice", "true_false"}
SUBJECTIVE_TYPES = {"accounting"}

EXAM_CONFIG = {
    "single_choice": {"count": 15, "score": 1},
    "multi_choice":  {"count": 10, "score": 2},
    "true_false":    {"count": 10, "score": 1},
    "accounting":    {"count": 6,  "score": 10},
}


# ============================================================
# 数据加载与保存
# ============================================================
@st.cache_data
def load_questions():
    with open(QUESTIONS_FILE, "r", encoding="utf-8") as f:
        return json.load(f)


def load_records():
    if os.path.exists(RECORDS_FILE):
        with open(RECORDS_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    return []


def save_records(records):
    with open(RECORDS_FILE, "w", encoding="utf-8") as f:
        json.dump(records, f, ensure_ascii=False, indent=2)


def add_record(q_id, q_type, user_answer, correct_answer, is_correct, self_eval=False):
    rec = {
        "date": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "question_id": q_id,
        "type": q_type,
        "user_answer": str(user_answer or ""),
        "correct_answer": str(correct_answer or ""),
        "is_correct": bool(is_correct),
        "self_evaluated": bool(self_eval),
    }
    st.session_state.records.append(rec)
    save_records(st.session_state.records)


# ============================================================
# 选项打乱
# ============================================================
def shuffle_options(original_options):
    if not original_options:
        return [], {}
    n = len(original_options)
    indices = list(range(n))
    random.shuffle(indices)
    display, new2orig = [], {}
    for new_i, old_i in enumerate(indices):
        new_letter = chr(65 + new_i)
        old_letter = chr(65 + old_i)
        new2orig[new_letter] = old_letter
        text = original_options[old_i]
        if ". " in text:
            text = text.split(". ", 1)[1]
        display.append(f"{new_letter}. {text}")
    return display, new2orig


def map_answer_back(user_new_letters, new2orig):
    result = [new2orig.get(ch, ch) for ch in user_new_letters]
    return "".join(sorted(result))


# ============================================================
# Session State 初始化
# ============================================================
def init_session():
    defaults = {
        "page": "随机刷题",
        "records": [],
        # --- 随机刷题 ---
        "rand_source": "全部",
        "rand_key_only": False,
        "rand_types": list(TYPE_LABELS.keys()),  # 题型筛选
        "rand_q": None,
        "rand_display_opts": [],
        "rand_new2orig": {},
        "rand_user_ans": None,
        "rand_submitted": False,
        "rand_correct": None,
        "rand_self_done": False,
        "rand_need_new": True,
        # --- 模拟考试 ---
        "exam_in_progress": False,
        "exam_questions": [],
        "exam_display_opts": {},
        "exam_new2orig": {},
        "exam_current_idx": 0,
        "exam_start_time": None,
        "exam_duration": 90 * 60,
        "exam_submitted": False,
        "exam_obj_score": 0,
        "exam_self_eval_idx": 0,
        "exam_self_evals": {},
        "exam_self_done": False,
        # --- 错题本 ---
        "err_idx": 0,
        "err_q": None,
        "err_display_opts": [],
        "err_new2orig": {},
        "err_user_ans": None,
        "err_submitted": False,
        "err_correct": None,
        "err_self_done": False,
        "err_need_new": True,
    }
    for k, v in defaults.items():
        if k not in st.session_state:
            st.session_state[k] = v
    if not st.session_state.records:
        st.session_state.records = load_records()


# ============================================================
# 辅助函数
# ============================================================
def get_wrong_ids():
    seen = set()
    wrong = []
    for r in st.session_state.records:
        if not r["is_correct"] and r["question_id"] not in seen:
            wrong.append(r["question_id"])
            seen.add(r["question_id"])
    return wrong


def type_badge(q_type):
    icon = TYPE_ICONS.get(q_type, "")
    label = TYPE_LABELS.get(q_type, q_type)
    css = "badge-obj" if q_type in OBJECTIVE_TYPES else "badge-sub"
    return f'<span class="type-badge {css}">{icon} {label}</span>'


def key_badge(is_key):
    """重点标记"""
    return '<span class="badge-key">⭐ 重点</span>' if is_key else ""


def source_badge(source):
    """来源标签：对章节显示蓝色，模拟卷显示绿色"""
    if "模拟" in source:
        return f'<span style="background:#e8f5e9;color:#2e7d32;padding:2px 8px;border-radius:10px;font-size:0.85em;">📋 {source}</span>'
    else:
        return f'<span style="background:#e3f2fd;color:#1565c0;padding:2px 8px;border-radius:10px;font-size:0.85em;">📖 {source}</span>'


# ============================================================
# 客观题控件（选项与勾选整合）
# ============================================================
def objective_input_inline(display_opts, q_type, key_prefix):
    """渲染客观题控件，选项文本即勾选项"""
    if q_type == "single_choice":
        choice = st.radio(
            " ",
            options=range(len(display_opts)),
            format_func=lambda i: display_opts[i],
            key=f"{key_prefix}_radio",
            index=None,
            label_visibility="collapsed",
        )
        st.session_state[key_prefix] = chr(65 + choice) if choice is not None else None

    elif q_type == "multi_choice":
        selected = []
        st.markdown("*可多选*")
        for i, opt_text in enumerate(display_opts):
            if st.checkbox(opt_text, key=f"{key_prefix}_cb_{i}"):
                selected.append(chr(65 + i))
        st.session_state[key_prefix] = "".join(sorted(selected)) if selected else ""

    elif q_type == "true_false":
        choice = st.radio(
            " ",
            options=["对", "错"],
            key=f"{key_prefix}_radio",
            index=None,
            horizontal=True,
            label_visibility="collapsed",
        )
        st.session_state[key_prefix] = choice if choice else None


def subjective_input_inline(key_prefix):
    st.text_area(
        "请在此作答（计算过程 / 会计分录）：",
        height=200,
        key=key_prefix,
        placeholder="请输入你的答案...",
        label_visibility="visible",
    )


# ============================================================
# 页面：随机刷题
# ============================================================
def page_random_practice():
    st.title("🎲 随机刷题")
    questions = load_questions()
    sources = sorted({q.get("source", "—") for q in questions})
    wrong_count = len(get_wrong_ids())

    # ---- 侧边栏 ----
    with st.sidebar:
        st.markdown("### 🔍 筛选条件")
        new_source = st.selectbox("来源", ["全部"] + sources, key="rand_source_sel")

        # 题型多选
        type_options = list(TYPE_LABELS.keys())
        type_labels_display = [f"{TYPE_ICONS[t]} {TYPE_LABELS[t]}" for t in type_options]
        selected_labels = st.multiselect(
            "题型（可多选）",
            type_labels_display,
            default=[f"{TYPE_ICONS[t]} {TYPE_LABELS[t]}" for t in st.session_state.rand_types],
            key="rand_types_sel"
        )
        new_types = [type_options[type_labels_display.index(l)] for l in selected_labels] if selected_labels else list(TYPE_LABELS.keys())

        # 仅重点
        new_key_only = st.checkbox("⭐ 仅重点考点", value=st.session_state.rand_key_only, key="rand_key_only_cb")

        if (new_source != st.session_state.rand_source or new_types != st.session_state.rand_types
                or new_key_only != st.session_state.rand_key_only):
            st.session_state.rand_source = new_source
            st.session_state.rand_types = new_types
            st.session_state.rand_key_only = new_key_only
            st.session_state.rand_need_new = True
            st.rerun()

        st.divider()
        st.markdown(f'<div class="sidebar-metric"><b>📕 错题数</b><br><span style="font-size:1.8em;">{wrong_count}</span></div>', unsafe_allow_html=True)

    # ---- 筛选题库 ----
    pool = [q for q in questions
            if (st.session_state.rand_source == "全部" or q.get("source") == st.session_state.rand_source)
            and q["type"] in st.session_state.rand_types
            and (not st.session_state.rand_key_only or q.get("key_point", False))]
    if not pool:
        st.warning("当前筛选条件下暂无题目，请调整筛选条件。")
        return

    # ---- 抽题 ----
    if st.session_state.rand_need_new:
        q = random.choice(pool)
        st.session_state.rand_q = q
        st.session_state.rand_submitted = False
        st.session_state.rand_correct = None
        st.session_state.rand_self_done = False
        st.session_state.rand_need_new = False
        if q["type"] in OBJECTIVE_TYPES:
            d, m = shuffle_options(q.get("options", []))
            st.session_state.rand_display_opts = d
            st.session_state.rand_new2orig = m
        else:
            st.session_state.rand_display_opts = []
            st.session_state.rand_new2orig = {}
        for k in list(st.session_state.keys()):
            if k.startswith("rand_user_ans") or k.startswith("rand_ans_"):
                del st.session_state[k]
        st.rerun()

    q = st.session_state.rand_q
    q_type = q["type"]

    # ---- 题目卡片 ----
    kp = key_badge(q.get("key_point", False))
    src = source_badge(q.get("source", "—"))
    st.markdown(
        f'<div class="question-card">'
        f'<p style="color:#888;font-size:0.85em;margin-bottom:6px;">'
        f'{type_badge(q_type)} &nbsp; {src} &nbsp; {kp} &nbsp; | &nbsp; 题号 #{q["id"]} &nbsp; | &nbsp; 候选池 {len(pool)} 题</p>'
        f'<h4>{q["question"]}</h4>',
        unsafe_allow_html=True
    )

    # ---- 未提交：作答区 ----
    if not st.session_state.rand_submitted:
        if q_type in OBJECTIVE_TYPES:
            disp = st.session_state.rand_display_opts
            objective_input_inline(disp, q_type, "rand_user_ans")
        else:
            subjective_input_inline("rand_user_ans_text")
            st.session_state.rand_user_ans = st.session_state.get("rand_user_ans_text", "")

        st.markdown("</div>", unsafe_allow_html=True)
        st.divider()

        c1, c2, c3 = st.columns([1, 1, 3])
        with c1:
            if st.button("✅ 提交答案", type="primary", use_container_width=True, key="rand_submit_btn"):
                ua = st.session_state.get("rand_user_ans", "")
                if q_type in OBJECTIVE_TYPES:
                    if not ua or not ua.strip():
                        st.warning("请先选择答案。")
                        st.stop()
                    mapped = map_answer_back(ua, st.session_state.rand_new2orig)
                    correct_ans = q["answer"].strip().upper()
                    is_correct = (mapped == correct_ans)
                    st.session_state.rand_correct = is_correct
                    add_record(q["id"], q_type, mapped, correct_ans, is_correct)
                else:
                    is_correct = None
                st.session_state.rand_submitted = True
                st.rerun()
        with c2:
            if st.button("⏭ 跳过", use_container_width=True, key="rand_skip_btn"):
                st.session_state.rand_need_new = True
                st.rerun()
    else:
        st.markdown("</div>", unsafe_allow_html=True)

        # ---- 判题结果 ----
        if q_type in OBJECTIVE_TYPES:
            if st.session_state.rand_correct:
                st.markdown('<div class="result-correct"><b>✅ 回答正确！</b></div>', unsafe_allow_html=True)
            else:
                st.markdown('<div class="result-wrong"><b>❌ 回答错误</b></div>', unsafe_allow_html=True)
                ua = st.session_state.get("rand_user_ans", "")
                st.markdown(f"**你的答案：** {ua}　　**正确答案：** {q['answer']}")
        else:
            st.markdown('<div class="info-card"><b>📝 主观题</b> — 请对比参考答案后自评</div>', unsafe_allow_html=True)

        # 解析
        if q.get("explanation"):
            with st.expander("📖 查看解析", expanded=(q_type in OBJECTIVE_TYPES and not st.session_state.rand_correct)):
                st.markdown(q["explanation"])

        # 主观题自评
        if q_type in SUBJECTIVE_TYPES:
            with st.expander("🔑 参考答案", expanded=True):
                st.markdown(q.get("answer", "暂无参考答案"))
            if q.get("explanation"):
                with st.expander("📖 解析"):
                    st.markdown(q["explanation"])

            if not st.session_state.rand_self_done:
                st.markdown("**请自评：**")
                c1, c2, c3 = st.columns(3)
                with c1:
                    if st.button("✅ 我做对了", type="primary", use_container_width=True, key="rand_self_right"):
                        add_record(q["id"], q_type, st.session_state.get("rand_user_ans_text", ""),
                                   q.get("answer", ""), True, self_eval=True)
                        st.session_state.rand_self_done = True
                        st.rerun()
                with c2:
                    if st.button("❌ 我做错了", use_container_width=True, key="rand_self_wrong"):
                        add_record(q["id"], q_type, st.session_state.get("rand_user_ans_text", ""),
                                   q.get("answer", ""), False, self_eval=True)
                        st.session_state.rand_self_done = True
                        st.rerun()

        # 下一题 / 收藏操作
        st.divider()
        c1, c2, c3 = st.columns([1, 1, 3])
        with c1:
            if st.button("➡️ 下一题", type="primary", use_container_width=True, key="rand_next"):
                st.session_state.rand_need_new = True
                st.rerun()
        with c2:
            wrong_ids = get_wrong_ids()
            in_wrong = q["id"] in wrong_ids
            lbl = "🔖 已收藏" if in_wrong else "📎 加入错题"
            if st.button(lbl, use_container_width=True, key="rand_bookmark"):
                if not in_wrong:
                    add_record(q["id"], q_type, "_bookmark_", q.get("answer", ""), False, self_eval=False)
                st.rerun()


# ============================================================
# 页面：模拟考试
# ============================================================
def page_mock_exam():
    st.title("📝 模拟考试")
    questions = load_questions()

    if not st.session_state.exam_in_progress and not st.session_state.exam_submitted:
        st.markdown("### 📋 考试说明")
        col_a, col_b = st.columns([2, 1])
        with col_a:
            st.markdown(f"""
            | 题型 | 题量 | 每题 | 满分 |
            |------|------|------|------|
            | 🔘 单选题 | 15 | 1分 | 15 |
            | ☑️ 多选题 | 10 | 2分 | 20 |
            | ⚖️ 判断题 | 10 | 1分 | 10 |
            | 📝 核算题 | 6 | 10分 | 60 |
            """)
        with col_b:
            st.markdown(f"""
            <div style="background:#f0f4ff;border-radius:12px;padding:20px;text-align:center;">
            <h1 style="color:#4A90D9;">105</h1>
            <p>总 分</p>
            <hr>
            <p>⏱ <b>90 分钟</b></p>
            <p style="font-size:0.8em;color:#888;">客观题自动判分<br>核算题交卷后自评</p>
            </div>
            """, unsafe_allow_html=True)

        for t, cfg in EXAM_CONFIG.items():
            available = len([q for q in questions if q["type"] == t])
            if available < cfg["count"]:
                st.warning(f"⚠️ 「{TYPE_LABELS[t]}」题库不足（需 {cfg['count']}，现有 {available}），将全部抽取。")

        if st.button("🚀 开始考试", type="primary", use_container_width=True):
            start_exam(questions)
            st.rerun()

    elif st.session_state.exam_in_progress and not st.session_state.exam_submitted:
        show_exam_page()
    elif st.session_state.exam_submitted:
        show_exam_result()


def start_exam(questions):
    selected = []
    for q_type, cfg in EXAM_CONFIG.items():
        pool = [q for q in questions if q["type"] == q_type]
        n = min(cfg["count"], len(pool))
        selected.extend(random.sample(pool, n))
    random.shuffle(selected)

    display_opts, new2orig_map = {}, {}
    for q in selected:
        if q["type"] in OBJECTIVE_TYPES:
            d, m = shuffle_options(q.get("options", []))
            display_opts[q["id"]] = d
            new2orig_map[q["id"]] = m

    for k in list(st.session_state.keys()):
        if k.startswith("exam_ans"):
            del st.session_state[k]

    st.session_state.exam_questions = selected
    st.session_state.exam_display_opts = display_opts
    st.session_state.exam_new2orig = new2orig_map
    st.session_state.exam_in_progress = True
    st.session_state.exam_submitted = False
    st.session_state.exam_current_idx = 0
    st.session_state.exam_start_time = time.time()
    st.session_state.exam_obj_score = 0
    st.session_state.exam_self_eval_idx = 0
    st.session_state.exam_self_evals = {}
    st.session_state.exam_self_done = False


def show_exam_page():
    total = len(st.session_state.exam_questions)
    idx = st.session_state.exam_current_idx
    q = st.session_state.exam_questions[idx]
    q_type = q["type"]

    elapsed = time.time() - st.session_state.exam_start_time
    remaining = max(0, st.session_state.exam_duration - elapsed)
    mins, secs = divmod(int(remaining), 60)

    # ---- 顶栏 ----
    with st.container():
        c_t, c_p, c_s, c_sub = st.columns([1, 2, 1, 1])
        with c_t:
            urgency = "🔴" if remaining < 600 else ("🟡" if remaining < 1800 else "⏱")
            st.markdown(f"<h2 style='text-align:center;'>{urgency} {mins:02d}:{secs:02d}</h2>", unsafe_allow_html=True)
            if remaining <= 0:
                st.error("⏰ 时间到！自动交卷。")
                submit_exam()
                st.rerun()
        with c_p:
            answered = sum(1 for qq in st.session_state.exam_questions
                          if st.session_state.get(f"exam_ans_{qq['id']}", "").strip())
            st.progress((idx + 1) / total, text=f"第 {idx+1}/{total} 题  ·  已答 {answered} 题")
        with c_s:
            st.markdown(f"<p style='text-align:center;padding-top:12px;'>{type_badge(q_type)}</p>", unsafe_allow_html=True)
        with c_sub:
            if st.button("📩 交卷", type="primary", use_container_width=True):
                submit_exam()
                st.rerun()

    st.divider()

    # ---- 题目卡片 ----
    st.markdown(
        f'<div class="question-card">'
        f'<h4>{q["question"]}</h4>',
        unsafe_allow_html=True
    )

    # 作答（选项与控件整合）
    ans_key = f"exam_ans_{q['id']}"
    if q_type in OBJECTIVE_TYPES:
        disp = st.session_state.exam_display_opts.get(q["id"], [])
        objective_input_inline(disp, q_type, ans_key)
    else:
        subjective_input_inline(ans_key)

    st.markdown("</div>", unsafe_allow_html=True)

    # ---- 底部导航 ----
    st.divider()
    c1, c2, c3 = st.columns([1, 1, 1])
    with c1:
        if idx > 0:
            if st.button("⬅️ 上一题", use_container_width=True):
                st.session_state.exam_current_idx -= 1
                st.rerun()
    with c2:
        # 答题卡跳转
        qids = [f"#{i+1} {TYPE_LABELS.get(qq['type'],'')[:2]}" for i, qq in enumerate(st.session_state.exam_questions)]
        jump = st.selectbox("跳转", ["—"] + qids, label_visibility="collapsed", key="exam_jump")
        if jump and jump != "—":
            ji = qids.index(jump)
            st.session_state.exam_current_idx = ji
            st.rerun()
    with c3:
        if idx < total - 1:
            if st.button("下一题 ➡️", use_container_width=True):
                st.session_state.exam_current_idx += 1
                st.rerun()


def submit_exam():
    for q in st.session_state.exam_questions:
        if q["type"] not in OBJECTIVE_TYPES:
            continue
        ans_key = f"exam_ans_{q['id']}"
        ua = (st.session_state.get(ans_key, "") or "").strip()
        n2o = st.session_state.exam_new2orig.get(q["id"], {})
        mapped = map_answer_back(ua, n2o)
        correct = q["answer"].strip().upper()
        is_correct = (mapped == correct)
        if is_correct:
            st.session_state.exam_obj_score += EXAM_CONFIG[q["type"]]["score"]
        add_record(q["id"], q["type"], mapped, correct, is_correct)

    st.session_state.exam_in_progress = False
    st.session_state.exam_submitted = True
    st.session_state.exam_self_eval_idx = 0
    st.session_state.exam_self_evals = {}
    st.session_state.exam_self_done = False


def show_exam_result():
    subj_qs = [q for q in st.session_state.exam_questions if q["type"] in SUBJECTIVE_TYPES]
    st.title("📊 考试结果")

    if not st.session_state.exam_self_done and subj_qs:
        ev_idx = st.session_state.exam_self_eval_idx
        if ev_idx < len(subj_qs):
            sq = subj_qs[ev_idx]
            st.markdown(f"### 📝 核算题自评（{ev_idx+1}/{len(subj_qs)}）")

            st.markdown(
                f'<div class="question-card"><h4>{sq["question"]}</h4>',
                unsafe_allow_html=True
            )
            ans_key = f"exam_ans_{sq['id']}"
            ua = st.session_state.get(ans_key, "")
            st.markdown("**你的作答：**")
            st.text(ua if ua else "（未作答）")
            st.markdown("</div>", unsafe_allow_html=True)

            with st.expander("🔑 参考答案", expanded=True):
                st.markdown(sq.get("answer", "暂无"))
            if sq.get("explanation"):
                with st.expander("📖 解析"):
                    st.markdown(sq["explanation"])

            st.divider()
            c1, c2, c3 = st.columns(3)
            with c1:
                if st.button("✅ 做对了", type="primary", use_container_width=True, key=f"ev_r_{ev_idx}"):
                    st.session_state.exam_self_evals[sq["id"]] = True
                    add_record(sq["id"], sq["type"], str(ua), sq.get("answer", ""), True, self_eval=True)
                    st.session_state.exam_self_eval_idx += 1
                    if st.session_state.exam_self_eval_idx >= len(subj_qs):
                        st.session_state.exam_self_done = True
                    st.rerun()
            with c2:
                if st.button("❌ 做错了", use_container_width=True, key=f"ev_w_{ev_idx}"):
                    st.session_state.exam_self_evals[sq["id"]] = False
                    add_record(sq["id"], sq["type"], str(ua), sq.get("answer", ""), False, self_eval=True)
                    st.session_state.exam_self_eval_idx += 1
                    if st.session_state.exam_self_eval_idx >= len(subj_qs):
                        st.session_state.exam_self_done = True
                    st.rerun()
        else:
            st.session_state.exam_self_done = True
            st.rerun()
    else:
        obj_score = st.session_state.exam_obj_score
        subj_correct = sum(1 for v in st.session_state.exam_self_evals.values() if v)
        subj_total = len(subj_qs)
        subj_score = sum(EXAM_CONFIG[q["type"]]["score"] for q in subj_qs
                         if st.session_state.exam_self_evals.get(q["id"], False))
        total_score = obj_score + subj_score

        max_obj = sum(EXAM_CONFIG[q["type"]]["score"]
                      for q in st.session_state.exam_questions if q["type"] in OBJECTIVE_TYPES)
        max_subj = sum(EXAM_CONFIG[q["type"]]["score"] for q in subj_qs)
        max_score = max_obj + max_subj
        pct = total_score / max_score * 100 if max_score > 0 else 0

        # 成绩仪表盘
        st.markdown("### 🏆 最终成绩")
        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("客观题得分", f"{obj_score}/{max_obj}")
        with col2:
            st.metric("核算题自评", f"{subj_score}/{max_subj}", f"{subj_correct}/{subj_total} 道正确")
        with col3:
            color = "green" if pct >= 60 else "red"
            st.markdown(f"<h1 style='text-align:center;color:{color};'>{pct:.0f}<small style='font-size:0.4em;'>%</small></h1>", unsafe_allow_html=True)
            st.markdown(f"<p style='text-align:center;'>{total_score}/{max_score}</p>", unsafe_allow_html=True)

        # 逐题回顾
        st.divider()
        st.markdown("### 📋 逐题回顾")
        for i, q in enumerate(st.session_state.exam_questions):
            ans_key = f"exam_ans_{q['id']}"
            ua = st.session_state.get(ans_key, "")
            icon = "✅" if (
                q["type"] in OBJECTIVE_TYPES and
                map_answer_back(ua.strip(), st.session_state.exam_new2orig.get(q["id"], {})) == q["answer"].strip().upper()
            ) or st.session_state.exam_self_evals.get(q["id"], False) else "❌"
            with st.expander(f"{icon} 第{i+1}题 — {TYPE_LABELS.get(q['type'], q['type'])} — {q['question'][:30]}..."):
                st.markdown(f"**题目：** {q['question']}")
                st.markdown(f"**你的答案：** {ua or '（未作答）'}")
                st.markdown(f"**正确答案：** {q.get('answer', '见参考答案')}")
                if q.get("explanation"):
                    st.markdown(f"**解析：** {q['explanation']}")

        st.divider()
        if st.button("🔄 重新考试", type="primary", use_container_width=True):
            reset_exam_state()
            st.rerun()


def reset_exam_state():
    for k in list(st.session_state.keys()):
        if k.startswith("exam_"):
            del st.session_state[k]


# ============================================================
# 页面：错题本
# ============================================================
def page_error_book():
    st.title("📕 错题本")
    questions = load_questions()
    q_map = {q["id"]: q for q in questions}
    wrong_ids = get_wrong_ids()

    if not wrong_ids:
        st.success("🎉 错题本空空如也，继续保持！")
        return

    st.markdown(f"共 **{len(wrong_ids)}** 道错题待复习")

    if st.session_state.err_need_new:
        st.session_state.err_idx = 0
        st.session_state.err_q = None
        st.session_state.err_display_opts = []
        st.session_state.err_new2orig = {}
        st.session_state.err_user_ans = None
        st.session_state.err_submitted = False
        st.session_state.err_correct = None
        st.session_state.err_self_done = False
        st.session_state.err_need_new = False
        for k in list(st.session_state.keys()):
            if k.startswith("err_ans_") or k.startswith("err_user_ans"):
                del st.session_state[k]
        st.rerun()

    idx = st.session_state.err_idx
    if idx >= len(wrong_ids):
        st.success("🎉 已复习完所有错题！")
        if st.button("🔁 重新开始", use_container_width=True):
            st.session_state.err_idx = 0
            st.session_state.err_need_new = True
            st.rerun()
        return

    qid = wrong_ids[idx]
    q = q_map.get(qid)
    if not q:
        st.session_state.err_idx += 1
        st.rerun()

    q_type = q["type"]
    st.progress((idx + 1) / len(wrong_ids), text=f"错题 {idx+1}/{len(wrong_ids)}  |  {TYPE_LABELS.get(q_type, q_type)}")

    # 打乱选项
    if q_type in OBJECTIVE_TYPES and not st.session_state.err_display_opts:
        d, m = shuffle_options(q.get("options", []))
        st.session_state.err_display_opts = d
        st.session_state.err_new2orig = m

    # 题目卡片
    kp = key_badge(q.get("key_point", False))
    src = source_badge(q.get("source", "—"))
    st.markdown(
        f'<div class="question-card">'
        f'<p style="color:#888;font-size:0.85em;">{type_badge(q_type)} &nbsp; {src} &nbsp; {kp} &nbsp;|&nbsp; 题号 #{q["id"]}</p>'
        f'<h4>{q["question"]}</h4>',
        unsafe_allow_html=True
    )

    if not st.session_state.err_submitted:
        if q_type in OBJECTIVE_TYPES:
            objective_input_inline(st.session_state.err_display_opts, q_type, "err_user_ans")
        else:
            subjective_input_inline("err_user_ans_text")
            st.session_state.err_user_ans = st.session_state.get("err_user_ans_text", "")
        st.markdown("</div>", unsafe_allow_html=True)

        st.divider()
        if st.button("✅ 提交", type="primary", use_container_width=True, key="err_submit_btn"):
            ua = st.session_state.get("err_user_ans", "")
            if q_type in OBJECTIVE_TYPES:
                if not ua or not ua.strip():
                    st.warning("请先作答。")
                    st.stop()
                mapped = map_answer_back(ua, st.session_state.err_new2orig)
                correct = q["answer"].strip().upper()
                st.session_state.err_correct = (mapped == correct)
                add_record(q["id"], q_type, mapped, correct, st.session_state.err_correct)
            else:
                st.session_state.err_correct = None
            st.session_state.err_submitted = True
            st.rerun()
    else:
        st.markdown("</div>", unsafe_allow_html=True)

        if q_type in OBJECTIVE_TYPES:
            if st.session_state.err_correct:
                st.markdown('<div class="result-correct"><b>✅ 这次做对了！已从错题本移除。</b></div>', unsafe_allow_html=True)
            else:
                st.markdown('<div class="result-wrong"><b>❌ 仍然错误，继续加油！</b></div>', unsafe_allow_html=True)
                st.markdown(f"**你的答案：** {st.session_state.get('err_user_ans', '')}　　**正确答案：** {q['answer']}")
        else:
            st.markdown('<div class="info-card"><b>📝 核算题</b> — 请自评</div>', unsafe_allow_html=True)
            with st.expander("🔑 参考答案", expanded=True):
                st.markdown(q.get("answer", "暂无"))
            if not st.session_state.err_self_done:
                c1, c2 = st.columns(2)
                with c1:
                    if st.button("✅ 做对了", type="primary", key="err_self_r", use_container_width=True):
                        add_record(q["id"], q_type, st.session_state.get("err_user_ans_text", ""),
                                   q.get("answer", ""), True, self_eval=True)
                        st.session_state.err_self_done = True
                        st.session_state.err_correct = True
                        st.rerun()
                with c2:
                    if st.button("❌ 做错了", key="err_self_w", use_container_width=True):
                        add_record(q["id"], q_type, st.session_state.get("err_user_ans_text", ""),
                                   q.get("answer", ""), False, self_eval=True)
                        st.session_state.err_self_done = True
                        st.session_state.err_correct = False
                        st.rerun()

        if q.get("explanation"):
            with st.expander("📖 查看解析", expanded=True):
                st.markdown(q["explanation"])

        st.divider()
        if st.button("➡️ 下一题", type="primary", use_container_width=True, key="err_next"):
            st.session_state.err_idx += 1
            st.session_state.err_q = None
            st.session_state.err_display_opts = []
            st.session_state.err_new2orig = {}
            st.session_state.err_user_ans = None
            st.session_state.err_submitted = False
            st.session_state.err_correct = None
            st.session_state.err_self_done = False
            st.rerun()


# ============================================================
# 页面：学习统计
# ============================================================
def page_statistics():
    st.title("📈 学习统计")
    records = st.session_state.records
    questions = load_questions()
    q_map = {q["id"]: q for q in questions}

    if not records:
        st.info("暂无做题记录，快去刷几道题吧！")
        return

    total = len(records)
    correct = sum(1 for r in records if r["is_correct"])
    wrong = total - correct
    rate = correct / total * 100 if total > 0 else 0

    # 概览卡片
    st.markdown("### 📊 总体概览")
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("总练习次数", total)
    c2.metric("正确", correct)
    c3.metric("错误", wrong)
    c4.metric("正确率", f"{rate:.1f}%")

    # 按题型
    st.divider()
    st.markdown("### 📋 按题型统计")
    type_stats = {}
    for r in records:
        t = r["type"]
        type_stats.setdefault(t, {"total": 0, "correct": 0})
        type_stats[t]["total"] += 1
        if r["is_correct"]:
            type_stats[t]["correct"] += 1

    if type_stats:
        cols = st.columns(len(type_stats))
        for i, (t, s) in enumerate(sorted(type_stats.items())):
            r = s["correct"] / s["total"] * 100 if s["total"] > 0 else 0
            with cols[i]:
                st.metric(TYPE_LABELS.get(t, t), f"{r:.0f}%", f"{s['correct']}/{s['total']}")

    # 按来源
    st.divider()
    st.markdown("### 🏷️ 按来源统计")
    source_stats = {}
    for r in records:
        q = q_map.get(r["question_id"])
        src = q.get("source", "未知") if q else "未知"
        source_stats.setdefault(src, {"total": 0, "correct": 0})
        source_stats[src]["total"] += 1
        if r["is_correct"]:
            source_stats[src]["correct"] += 1

    for src, s in sorted(source_stats.items()):
        rate = s["correct"] / s["total"] * 100 if s["total"] > 0 else 0
        st.progress(rate / 100, text=f"{src}：{rate:.1f}%（{s['correct']}/{s['total']}）")

    # 最近记录
    st.divider()
    st.markdown("### 📜 最近 20 条记录")
    recent = sorted(records, key=lambda r: r.get("date", ""), reverse=True)[:20]
    for r in recent:
        q = q_map.get(r["question_id"])
        q_text = (q["question"][:40] + "...") if q else f"题目ID:{r['question_id']}"
        icon = "✅" if r["is_correct"] else "❌"
        tag = " [自评]" if r.get("self_evaluated") else ""
        st.markdown(f"{icon} `{r.get('date','')[:16]}` {TYPE_LABELS.get(r['type'], r['type'])}{tag} — {q_text}")


# ============================================================
# 主入口
# ============================================================
def main():
    init_session()

    with st.sidebar:
        st.markdown("# 📚 中级财务会计刷题")
        st.caption("中级财务会计 · 备考刷题系统")
        st.divider()

        pages = ["🎲 随机刷题", "📝 模拟考试", "📕 错题本", "📈 学习统计"]
        page_labels = ["随机刷题", "模拟考试", "错题本", "学习统计"]
        default_idx = page_labels.index(st.session_state.page) if st.session_state.page in page_labels else 0
        selected = st.radio("", pages, index=default_idx, label_visibility="visible")
        new_page = page_labels[pages.index(selected)]
        if new_page != st.session_state.page:
            st.session_state.page = new_page
            st.rerun()

        st.divider()
        questions_count = len(load_questions())
        records_count = len(st.session_state.records)
        st.caption(f"📦 题库：{questions_count} 题  ·  📋 记录：{records_count} 条")
        wrong_count = len(get_wrong_ids())
        st.caption(f"📕 错题：{wrong_count} 道")

    page_map = {
        "随机刷题": page_random_practice,
        "模拟考试": page_mock_exam,
        "错题本": page_error_book,
        "学习统计": page_statistics,
    }
    page_map[st.session_state.page]()


if __name__ == "__main__":
    main()
