"""第二层：真实模型端到端冒烟（需已配置 MODEL_API_KEY，否则自动跳过）。

运行：.venv/bin/python -m pytest tests/test_real_model_smoke.py -v
"""
from datetime import datetime

import pytest

from app.services import llm

pytestmark = pytest.mark.skipif(
    not llm.is_configured(),
    reason="未配置 MODEL_API_KEY，跳过真实模型冒烟",
)


def test_real_model_chat():
    out = llm.chat_completion(
        [{"role": "user", "content": "只回复两个字：收到"}], max_tokens=20
    )
    assert out.strip()


def test_real_model_end_to_end():
    from app.services import agent

    r = agent.handle("明早杭州周边两小时，想打翘嘴", None)
    assert r["type"] == "plan"
    assert r["reply"].strip()
    assert r["plan"].best_window


def test_real_model_slot_extraction():
    ctx = llm.extract_slots_llm("周六早上杭州附近打鳜鱼，只有一小时", datetime.now())
    assert ctx is not None
    assert ctx.target_species == "鳜鱼"
    assert ctx.location
