"""GA-Shift Agno Chat UI.

Streamlit チャットインターフェースで ShiftTeam と対話し、
シフト最適化を実行する。

Usage:
    streamlit run src/ga_shift/ui/chat_app.py
    uv run streamlit run src/ga_shift/ui/chat_app.py
"""

from __future__ import annotations

import asyncio
import os
from pathlib import Path

import streamlit as st

# ---------------------------------------------------------------------------
# Page config
# ---------------------------------------------------------------------------
st.set_page_config(
    page_title="GA-shift チャット",
    page_icon="🗓️",
    layout="wide",
)


# ---------------------------------------------------------------------------
# Session state initialization
# ---------------------------------------------------------------------------
if "messages" not in st.session_state:
    st.session_state.messages = []

if "team" not in st.session_state:
    st.session_state.team = None

if "facility_name" not in st.session_state:
    st.session_state.facility_name = ""


# ---------------------------------------------------------------------------
# Helper: lazy-init the ShiftTeam
# ---------------------------------------------------------------------------
def _get_team():
    """ShiftTeam をセッション内で一度だけ初期化する。"""
    if st.session_state.team is not None:
        return st.session_state.team

    from ga_shift.agno_agents.team import create_shift_team

    # MCP server command - uvを使ってga_shift.mcpモジュールを起動
    mcp_cmd = os.environ.get(
        "GA_SHIFT_MCP_CMD",
        "uv run python -m ga_shift.mcp",
    )

    team = create_shift_team(
        mcp_server_command=mcp_cmd,
        enable_memory=True,
    )
    st.session_state.team = team
    return team


# ---------------------------------------------------------------------------
# Sidebar: File upload / download + settings
# ---------------------------------------------------------------------------
with st.sidebar:
    st.header("📁 ファイル操作")

    # Excel upload
    uploaded = st.file_uploader(
        "希望休Excel をアップロード",
        type=["xlsx"],
        help="テンプレートに希望休を入力したExcelファイルをアップロードしてください。",
    )
    if uploaded is not None:
        # Save uploaded file to temp dir
        upload_dir = Path("data/uploads")
        upload_dir.mkdir(parents=True, exist_ok=True)
        upload_path = upload_dir / uploaded.name
        upload_path.write_bytes(uploaded.getvalue())
        st.success(f"✅ アップロード完了: {uploaded.name}")
        st.session_state["uploaded_file"] = str(upload_path)

    # Download section
    st.divider()
    st.subheader("📥 生成ファイル")
    output_dir = Path("data/ga_shift_output")
    if output_dir.exists():
        xlsx_files = sorted(output_dir.glob("*.xlsx"), key=lambda p: p.stat().st_mtime, reverse=True)
        for f in xlsx_files[:5]:  # Show last 5 files
            with open(f, "rb") as fp:
                st.download_button(
                    label=f"⬇️ {f.name}",
                    data=fp.read(),
                    file_name=f.name,
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                    key=f"dl_{f.name}",
                )
    else:
        st.info("まだ生成ファイルはありません。")

    # Settings
    st.divider()
    st.subheader("⚙️ 設定")
    facility_name = st.text_input(
        "事業所名",
        value=st.session_state.facility_name,
        placeholder="例: 木町家",
    )
    if facility_name != st.session_state.facility_name:
        st.session_state.facility_name = facility_name

    if st.button("🔄 チャットをリセット"):
        st.session_state.messages = []
        st.session_state.team = None
        st.rerun()


# ---------------------------------------------------------------------------
# Main area: Chat UI
# ---------------------------------------------------------------------------
st.title("🗓️ GA-shift シフト最適化")
st.caption("対話でシフト表を自動生成 — 遺伝的アルゴリズム × AIアシスタント")

# Display chat history
for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])

# Chat input
if prompt := st.chat_input("シフトについて何でも聞いてください"):
    # Show user message
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)

    # Generate response
    with st.chat_message("assistant"):
        with st.spinner("考えています..."):
            try:
                team = _get_team()

                # Add context from uploaded file if available
                context_prompt = prompt
                if "uploaded_file" in st.session_state:
                    context_prompt += f"\n\n[アップロード済みファイル: {st.session_state['uploaded_file']}]"

                # Run the team (synchronous wrapper)
                response = team.run(context_prompt)

                if response and response.content:
                    assistant_msg = response.content
                else:
                    assistant_msg = "申し訳ございません、応答を生成できませんでした。もう一度お試しください。"

            except Exception as e:
                assistant_msg = f"エラーが発生しました: {e}\n\nMCPサーバーが起動していることを確認してください。"

        st.markdown(assistant_msg)
        st.session_state.messages.append({"role": "assistant", "content": assistant_msg})


# ---------------------------------------------------------------------------
# Welcome message
# ---------------------------------------------------------------------------
if not st.session_state.messages:
    with st.chat_message("assistant"):
        welcome = (
            "こんにちは！シフト最適化アシスタントです。\n\n"
            "以下のようなことができます：\n\n"
            "- **事業所の設定** — スタッフ情報やセクション構成を登録\n"
            "- **テンプレート生成** — 月次シフト入力用Excelを作成\n"
            "- **シフト最適化** — 遺伝的アルゴリズムで最適シフトを生成\n"
            "- **結果の確認・調整** — 生成結果の説明や手動修正\n\n"
            "まずは何をしたいか教えてください！"
        )
        st.markdown(welcome)
