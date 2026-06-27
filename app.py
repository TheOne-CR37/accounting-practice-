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
    /* ---- Notion-style global overrides ---- */
    html, body, [data-testid="stAppViewContainer"] {
        background: #FFFDF9;
    }
    h1,h2,h3,h4,h5,h6,p,li,label,span,div {
        color: #37352F;
    }
    /* 超薄边框 */
    hr, .stDivider { border-color: rgba(55,53,47,0.08); }

    /* ---- 题目卡片 ---- */
    .question-card {
        background: #FFFFFF;
        border-radius: 6px;
        padding: 24px;
        margin: 16px 0;
        border: 1px solid rgba(55,53,47,0.08);
        box-shadow: 0 1px 3px rgba(15,15,15,0.04);
    }
    /* ---- 结果卡片 ---- */
    .result-correct {
        background: rgba(15,123,78,0.06);
        border-radius: 6px;
        padding: 16px;
        border: 1px solid rgba(15,123,78,0.12);
        color: #37352F;
    }
    .result-wrong {
        background: rgba(224,62,62,0.06);
        border-radius: 6px;
        padding: 16px;
        border: 1px solid rgba(224,62,62,0.12);
        color: #37352F;
    }
    .info-card {
        background: rgba(35,131,226,0.06);
        border-radius: 6px;
        padding: 16px;
        border: 1px solid rgba(35,131,226,0.10);
    }
    /* ---- 侧边栏指标 ---- */
    .sidebar-metric {
        background: #2383E2;
        border-radius: 6px;
        padding: 16px;
        color: #FFFFFF;
        text-align: center;
        margin: 8px 0;
    }
    /* ---- 题型徽章 ---- */
    .type-badge {
        display: inline-block;
        padding: 2px 10px;
        border-radius: 4px;
        font-size: 0.82em;
        font-weight: 500;
    }
    .badge-obj { background: rgba(35,131,226,0.08); color: #2383E2; }
    .badge-sub { background: rgba(217,115,13,0.08); color: #D9730D; }
    /* ---- 重点标记 ---- */
    .badge-key {
        display: inline-block;
        background: rgba(224,62,62,0.08);
        color: #D93B3B;
        padding: 1px 8px;
        border-radius: 4px;
        font-size: 0.75em;
        font-weight: 600;
    }
    /* ---- Steamlit 控件微调 ---- */
    .stRadio > div { gap: 6px; }
    .stCheckbox > label { font-size: 1rem; color: #37352F; }
    /* ---- 按钮 ---- */
    .stButton > button {
        border-radius: 6px;
        font-weight: 500;
        transition: all 0.15s ease;
    }
    /* primary 按钮用 Notion 蓝 */
    .stButton > button[kind="primary"] {
        background: #2383E2;
        border-color: #2383E2;
    }
    /* ---- 进度条 ---- */
    .stProgress > div > div > div {
        background: #2383E2;
    }
    /* ---- 输入框 ---- */
    textarea, input, select {
        border: 1px solid rgba(55,53,47,0.12) !important;
        border-radius: 6px !important;
    }
</style>
""", unsafe_allow_html=True)

# ============================================================
# 文件路径
# ============================================================
BASE_DIR = Path(__file__).parent
QUESTIONS_FILE = BASE_DIR / "questions.json"
RECORDS_FILE = BASE_DIR / "records.json"
BOOKMARKS_FILE = BASE_DIR / "bookmarks.json"
MASTERY_FILE = BASE_DIR / "mastery.json"

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
@st.cache_data(ttl=600)
def load_questions():
    """加载题库，缓存10分钟自动刷新"""
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
    # update mastery
    _update_mastery(q_id, is_correct)


# ---- 收藏夹 ----
def load_bookmarks():
    if os.path.exists(BOOKMARKS_FILE):
        with open(BOOKMARKS_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    return []


def save_bookmarks(bm):
    with open(BOOKMARKS_FILE, "w", encoding="utf-8") as f:
        json.dump(bm, f, ensure_ascii=False, indent=2)


def toggle_bookmark(q_id):
    if q_id in st.session_state.bookmarks:
        st.session_state.bookmarks.remove(q_id)
    else:
        st.session_state.bookmarks.append(q_id)
    save_bookmarks(st.session_state.bookmarks)


# ---- 掌握度追踪（连续做对 2 次才从错题本移除） ----
def load_mastery():
    if os.path.exists(MASTERY_FILE):
        with open(MASTERY_FILE, "r", encoding="utf-8") as f:
            return {int(k): v for k, v in json.load(f).items()}
    return {}


def save_mastery(m):
    with open(MASTERY_FILE, "w", encoding="utf-8") as f:
        json.dump({str(k): v for k, v in m.items()}, f, ensure_ascii=False, indent=2)


def _update_mastery(q_id, is_correct):
    """每次作答后更新掌握度：做对+1，做错清零"""
    m = st.session_state.err_mastery
    if is_correct:
        m[q_id] = m.get(q_id, 0) + 1
    else:
        m[q_id] = 0
    save_mastery(m)


# ---- 核算题答案折叠 ----
import re


def collapsible_answer(answer_text, prefix="ans"):
    """将长答案按 ①/（1）/1）/步骤 分段折叠展示"""
    if not answer_text:
        st.markdown("暂无参考答案")
        return
    # 按明显的分段标记切分
    pattern = r"(?=(?:^|\n)\s*(?:[①②③④⑤⑥⑦⑧⑨⑩]|\(\d+\)|\d+\s*[）\)]|（\d+）))"
    parts = re.split(pattern, answer_text, flags=re.MULTILINE)
    # 过滤空段
    parts = [p.strip() for p in parts if p.strip()]
    if len(parts) <= 1:
        # 尝试按空行分段
        parts = [p.strip() for p in re.split(r"\n{2,}", answer_text) if p.strip()]
    if len(parts) <= 1:
        st.markdown(answer_text)
        return
    # 超过 3 段才折叠，否则直接展示
    if len(parts) <= 3:
        for p in parts:
            st.markdown(p)
        return
    # 折叠展示：前 2 段展开，其余折叠
    for i, p in enumerate(parts):
        if i < 2:
            st.markdown(p)
        else:
            title = p.split("\n")[0][:40] if p else f"步骤 {i+1}"
            with st.expander(f"📋 {title}…", expanded=False):
                st.markdown(p)


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
        "bookmarks": [],
        "err_mastery": {},
        # --- 随机刷题 ---
        "rand_source": "全部",
        "rand_key_only": False,
        "rand_types": list(TYPE_LABELS.keys()),
        "rand_q": None,
        "rand_display_opts": [],
        "rand_new2orig": {},
        "rand_user_ans": None,
        "rand_submitted": False,
        "rand_correct": None,
        "rand_self_done": False,
        "rand_need_new": True,
        # --- 模拟考试 ---
        "exam_source": "全部",
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
        "err_source": "全部",
        "err_types": list(TYPE_LABELS.keys()),
    }
    for k, v in defaults.items():
        if k not in st.session_state:
            st.session_state[k] = v
    if not st.session_state.records:
        st.session_state.records = load_records()
    if not st.session_state.bookmarks:
        st.session_state.bookmarks = load_bookmarks()
    if not st.session_state.err_mastery:
        st.session_state.err_mastery = load_mastery()


# ============================================================
# 辅助函数
# ============================================================
def get_wrong_ids():
    """错题 = 历史有错误记录 且 尚未掌握（连续正确 < 2 次）"""
    seen = set()
    wrong = []
    for r in st.session_state.records:
        if not r["is_correct"] and r["question_id"] not in seen:
            wrong.append(r["question_id"])
            seen.add(r["question_id"])
    # 过滤已掌握的（连续做对 >= 2 次）
    mastery = st.session_state.get("err_mastery", {})
    return [w for w in wrong if mastery.get(w, 0) < 2]


def type_badge(q_type):
    icon = TYPE_ICONS.get(q_type, "")
    label = TYPE_LABELS.get(q_type, q_type)
    css = "badge-obj" if q_type in OBJECTIVE_TYPES else "badge-sub"
    return f'<span class="type-badge {css}">{icon} {label}</span>'


def key_badge(is_key):
    """重点标记"""
    return '<span class="badge-key">⭐ 重点</span>' if is_key else ""


def source_badge(source):
    """来源标签：章节暖灰，模拟卷暖绿"""
    if "模拟" in source:
        return f'<span style="background:rgba(15,123,78,0.07);color:#0F7B4E;padding:2px 8px;border-radius:4px;font-size:0.82em;">📋 {source}</span>'
    else:
        return f'<span style="background:rgba(55,53,47,0.04);color:#6B6966;padding:2px 8px;border-radius:4px;font-size:0.82em;">📖 {source}</span>'


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
    bm = "⭐" if q["id"] in st.session_state.bookmarks else ""
    st.markdown(
        f'<div class="question-card">'
        f'<p style="color:#9B9A97;font-size:0.85em;margin-bottom:6px;">'
        f'{type_badge(q_type)} &nbsp; {src} &nbsp; {kp} &nbsp; {bm} &nbsp; | &nbsp; 题号 #{q["id"]} &nbsp; | &nbsp; 候选池 {len(pool)} 题</p>'
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
            st.markdown("**参考答案：**")
            collapsible_answer(q.get("answer", "暂无参考答案"), f"rand_ans_{q['id']}")
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
            is_bm = q["id"] in st.session_state.bookmarks
            lbl = "⭐ 已收藏" if is_bm else "☆ 收藏"
            if st.button(lbl, use_container_width=True, key="rand_bookmark"):
                toggle_bookmark(q["id"])
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
            <div style="background:#FFFFFF;border-radius:6px;padding:24px;text-align:center;border:1px solid rgba(55,53,47,0.08);box-shadow:0 1px 3px rgba(15,15,15,0.04);">
            <h1 style="color:#2383E2;margin-bottom:0;">105</h1>
            <p style="color:#9B9A97;margin-top:4px;">总 分</p>
            <hr style="border-color:rgba(55,53,47,0.06);">
            <p style="color:#37352F;">⏱ <b>90 分钟</b></p>
            <p style="font-size:0.8em;color:#9B9A97;">客观题自动判分<br>核算题交卷后自评</p>
            </div>
            """, unsafe_allow_html=True)

        # 来源筛选
        sources = sorted({q.get("source", "—") for q in questions})
        col_src, _ = st.columns([1, 2])
        with col_src:
            exam_src = st.selectbox("📂 考试范围", ["全部"] + sources, key="exam_source_sel")
            st.session_state.exam_source = exam_src

        for t, cfg in EXAM_CONFIG.items():
            pool = [q for q in questions if q["type"] == t
                    and (exam_src == "全部" or q.get("source") == exam_src)]
            available = len(pool)
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
    exam_src = st.session_state.get("exam_source", "全部")
    selected = []
    for q_type, cfg in EXAM_CONFIG.items():
        pool = [q for q in questions if q["type"] == q_type
                and (exam_src == "全部" or q.get("source") == exam_src)]
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
                collapsible_answer(sq.get("answer", "暂无"), f"ev_ans_{sq['id']}")
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
            color = "#0F7B4E" if pct >= 60 else "#D93B3B"
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
    all_wrong_ids = get_wrong_ids()
    sources = sorted({q_map.get(w, {}).get("source", "—") for w in all_wrong_ids if w in q_map})

    # ---- 侧边栏筛选 ----
    with st.sidebar:
        st.markdown("### 🔍 错题筛选")
        new_err_source = st.selectbox("来源", ["全部"] + sources, key="err_source_sel")
        type_options = list(TYPE_LABELS.keys())
        type_labels_display = [f"{TYPE_ICONS[t]} {TYPE_LABELS[t]}" for t in type_options]
        sel = st.multiselect(
            "题型", type_labels_display,
            default=[f"{TYPE_ICONS[t]} {TYPE_LABELS[t]}" for t in st.session_state.err_types],
            key="err_types_sel"
        )
        new_err_types = [type_options[type_labels_display.index(l)] for l in sel] if sel else list(TYPE_LABELS.keys())

        if new_err_source != st.session_state.err_source or new_err_types != st.session_state.err_types:
            st.session_state.err_source = new_err_source
            st.session_state.err_types = new_err_types
            st.session_state.err_need_new = True
            st.rerun()

        # 掌握度统计
        mastery = st.session_state.err_mastery
        mastered = sum(1 for w in all_wrong_ids if mastery.get(w, 0) >= 2)
        st.divider()
        st.metric("已掌握", mastered)
        st.metric("待复习", len(all_wrong_ids))

    # 按筛选条件过滤
    wrong_ids = [w for w in all_wrong_ids
                 if w in q_map
                 and (st.session_state.err_source == "全部" or q_map[w].get("source") == st.session_state.err_source)
                 and q_map[w]["type"] in st.session_state.err_types]

    if not all_wrong_ids:
        st.success("🎉 没有尚未掌握的错题，继续保持！")
        return

    if not wrong_ids:
        st.info("当前筛选条件下暂无错题。")
        return

    st.markdown(f"待复习 **{len(wrong_ids)}** 道（共 {len(all_wrong_ids)} 道）")

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
        st.success("🎉 当前筛选下已复习完所有错题！")
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
    mc = mastery.get(qid, 0)

    st.progress((idx + 1) / len(wrong_ids),
                text=f"错题 {idx+1}/{len(wrong_ids)} | {TYPE_LABELS.get(q_type, q_type)} | 连续正确 {mc}/2")

    # 打乱选项
    if q_type in OBJECTIVE_TYPES and not st.session_state.err_display_opts:
        d, m = shuffle_options(q.get("options", []))
        st.session_state.err_display_opts = d
        st.session_state.err_new2orig = m

    # 题目卡片
    kp = key_badge(q.get("key_point", False))
    src = source_badge(q.get("source", "—"))
    bm = "⭐" if qid in st.session_state.bookmarks else ""
    st.markdown(
        f'<div class="question-card">'
        f'<p style="color:#9B9A97;font-size:0.85em;">{type_badge(q_type)} &nbsp; {src} &nbsp; {kp} &nbsp; {bm} &nbsp;|&nbsp; 题号 #{q["id"]}</p>'
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
        c1, c2, c3 = st.columns([1, 1, 2])
        with c1:
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
        with c2:
            lbl = "⭐ 已收藏" if qid in st.session_state.bookmarks else "☆ 收藏"
            if st.button(lbl, use_container_width=True, key="err_bm_btn"):
                toggle_bookmark(qid)
                st.rerun()
    else:
        st.markdown("</div>", unsafe_allow_html=True)

        if q_type in OBJECTIVE_TYPES:
            if st.session_state.err_correct:
                new_mc = st.session_state.err_mastery.get(qid, 0)
                if new_mc >= 2:
                    st.markdown(f'<div class="result-correct"><b>✅ 连续正确 {new_mc} 次，已掌握！从错题本移除。</b></div>', unsafe_allow_html=True)
                else:
                    st.markdown(f'<div class="result-correct"><b>✅ 做对了！连续正确 {new_mc}/2 次</b> — 再对 1 次即可移除</div>', unsafe_allow_html=True)
            else:
                st.markdown(f'<div class="result-wrong"><b>❌ 仍然错误，继续加油！</b>（连续正确清零）</div>', unsafe_allow_html=True)
                st.markdown(f"**你的答案：** {st.session_state.get('err_user_ans', '')}　　**正确答案：** {q['answer']}")
        else:
            st.markdown('<div class="info-card"><b>📝 核算题</b> — 请自评</div>', unsafe_allow_html=True)
            st.markdown("**参考答案：**")
            collapsible_answer(q.get("answer", "暂无"), f"err_ans_{qid}")
            if not st.session_state.err_self_done:
                c1, c2, c3 = st.columns(3)
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
        c1, c2 = st.columns([1, 3])
        with c1:
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
# 页面：收藏夹
# ============================================================
def page_bookmarks():
    st.title("📌 收藏夹")
    questions = load_questions()
    q_map = {q["id"]: q for q in questions}
    bm_ids = st.session_state.bookmarks

    if not bm_ids:
        st.info("暂无收藏，在刷题/错题本中点击 ☆ 收藏 即可添加。")
        return

    # 筛选
    bm_qs = [q_map[w] for w in bm_ids if w in q_map]
    sources = sorted({q.get("source", "—") for q in bm_qs})
    with st.sidebar:
        st.markdown("### 🔍 收藏筛选")
        filter_src = st.selectbox("来源", ["全部"] + sources, key="bm_source")
        type_options = list(TYPE_LABELS.keys())
        type_labels_display = [f"{TYPE_ICONS[t]} {TYPE_LABELS[t]}" for t in type_options]
        sel = st.multiselect("题型", type_labels_display, default=type_labels_display, key="bm_types")
        filter_types = [type_options[type_labels_display.index(l)] for l in sel] if sel else list(TYPE_LABELS.keys())

    filtered = [q for q in bm_qs
                if (filter_src == "全部" or q.get("source") == filter_src)
                and q["type"] in filter_types]

    st.markdown(f"共收藏 **{len(bm_ids)}** 题，当前显示 **{len(filtered)}** 题")

    for q in filtered:
        kp = key_badge(q.get("key_point", False))
        src = source_badge(q.get("source", "—"))
        with st.container():
            st.markdown(
                f'<div class="question-card">'
                f'<p style="color:#9B9A97;font-size:0.85em;">{type_badge(q["type"])} &nbsp; {src} &nbsp; {kp} &nbsp;|&nbsp; 题号 #{q["id"]} &nbsp;|&nbsp; 连续正确 {st.session_state.err_mastery.get(q["id"], 0)}/2</p>'
                f'<h4>{q["question"]}</h4>',
                unsafe_allow_html=True
            )
            # 答案
            if q["type"] in SUBJECTIVE_TYPES:
                with st.expander("🔑 参考答案"):
                    collapsible_answer(q.get("answer", ""), f"bm_ans_{q['id']}")
            else:
                st.markdown(f"**答案：** {q.get('answer', '')}")
                if q.get("explanation"):
                    with st.expander("📖 解析"):
                        st.markdown(q["explanation"])
            # 取消收藏
            if st.button("取消收藏", key=f"bm_rm_{q['id']}"):
                toggle_bookmark(q["id"])
                st.rerun()
            st.markdown("</div>", unsafe_allow_html=True)


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

        pages = ["🎲 随机刷题", "📝 模拟考试", "📕 错题本", "📌 收藏夹", "📈 学习统计"]
        page_labels = ["随机刷题", "模拟考试", "错题本", "收藏夹", "学习统计"]
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
        bm_count = len(st.session_state.bookmarks)
        st.caption(f"📕 错题：{wrong_count} 道  ·  ⭐ 收藏：{bm_count} 题")
        if st.button("🔄 清除缓存", use_container_width=True):
            st.cache_data.clear()
            st.rerun()

    page_map = {
        "随机刷题": page_random_practice,
        "模拟考试": page_mock_exam,
        "错题本": page_error_book,
        "收藏夹": page_bookmarks,
        "学习统计": page_statistics,
    }
    page_map[st.session_state.page]()


if __name__ == "__main__":
    main()
