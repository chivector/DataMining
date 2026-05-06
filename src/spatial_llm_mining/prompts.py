from __future__ import annotations

from dataclasses import dataclass
from hashlib import sha256
from typing import Iterable

import pandas as pd


@dataclass(frozen=True)
class Scenario:
    case_id: str
    stair_width_cm: int
    landing_depth_cm: int
    wheelchair_width_cm: int
    wheelchair_length_cm: int
    turn_radius_cm: int
    clearance_margin_cm: int
    reference_judgment: str
    criticality: str


def stable_int(*values: object, modulo: int = 10_000) -> int:
    text = "|".join(str(v) for v in values)
    return int(sha256(text.encode("utf-8")).hexdigest()[:12], 16) % modulo


def build_scenarios(num_cases: int = 20) -> list[Scenario]:
    widths = [82, 86, 90, 94, 98, 102, 106]
    landings = [88, 94, 100, 106, 112, 118, 124]
    chair_widths = [64, 66, 68, 70, 72, 74]
    chair_lengths = [105, 110, 115, 120]
    radii = [74, 78, 82, 86, 90, 94, 98, 102]

    scenarios: list[Scenario] = []
    for idx in range(num_cases):
        stair_width = widths[(idx * 3 + 1) % len(widths)]
        landing_depth = landings[(idx * 5 + 2) % len(landings)]
        chair_width = chair_widths[(idx * 2 + 1) % len(chair_widths)]
        chair_length = chair_lengths[(idx * 3) % len(chair_lengths)]
        turn_radius = radii[(idx * 4 + 3) % len(radii)]

        side_clearance = stair_width - chair_width
        turn_clearance = landing_depth - turn_radius
        margin = min(side_clearance, turn_clearance)
        if margin >= 10:
            judgment = "can_pass"
            criticality = "wide"
        elif margin >= 3:
            judgment = "can_pass"
            criticality = "borderline"
        elif margin >= -4:
            judgment = "cannot_pass"
            criticality = "borderline"
        else:
            judgment = "cannot_pass"
            criticality = "narrow"

        scenarios.append(
            Scenario(
                case_id=f"C{idx + 1:03d}",
                stair_width_cm=stair_width,
                landing_depth_cm=landing_depth,
                wheelchair_width_cm=chair_width,
                wheelchair_length_cm=chair_length,
                turn_radius_cm=turn_radius,
                clearance_margin_cm=margin,
                reference_judgment=judgment,
                criticality=criticality,
            )
        )
    return scenarios


def _qualitative_width(s: Scenario) -> str:
    if s.criticality == "wide":
        return "楼梯转角空间看起来还算宽裕，轮椅通过时两侧有一些余量"
    if s.reference_judgment == "can_pass":
        return "楼梯转角比较紧凑，轮椅宽度不小，但似乎还能勉强调整方向"
    return "楼梯转角很紧，轮椅比较宽，转过去时容易贴近墙面"


def render_prompt(s: Scenario, level: str, noise_text: str) -> str:
    suffix = f"\n无关环境信息：{noise_text}" if noise_text else ""
    question = "\n请判断电动轮椅能否顺利完成 90 度转弯，并给出推理过程。最后必须用“最终判断：能通过/不能通过/不确定”回答。"

    if level == "L1":
        body = (
            "场景：一台电动轮椅需要在楼梯附近的 90 度转角处转弯。"
            f"{_qualitative_width(s)}。请你根据空间常识判断。"
        )
    elif level == "L2":
        body = (
            "场景：一台电动轮椅需要在楼梯平台处完成 90 度转弯。"
            f"楼梯通道净宽 {s.stair_width_cm}cm，平台进深 {s.landing_depth_cm}cm，"
            f"轮椅宽 {s.wheelchair_width_cm}cm，轮椅长 {s.wheelchair_length_cm}cm，"
            f"厂家给出的最小转弯半径约为 {s.turn_radius_cm}cm。"
            "请基于这些参数判断是否能通过。"
        )
    elif level == "L3":
        body = (
            "场景：将楼梯转角抽象为 L 形通道。设内角为原点 O，"
            "第一段通道沿 x 轴正方向，第二段通道沿 y 轴正方向；"
            f"通道宽度 W={s.stair_width_cm}cm，平台有效进深 D={s.landing_depth_cm}cm。"
            f"轮椅近似为 {s.wheelchair_length_cm}cm x {s.wheelchair_width_cm}cm 的矩形刚体，"
            f"保守旋转包络半径 R={s.turn_radius_cm}cm。"
            "若旋转扫过包络与墙体边界相交，则视为不能顺利通过；否则视为可通过。"
        )
    else:
        raise ValueError(f"Unknown level: {level}")
    return body + suffix + question


def build_prompt_matrix(
    levels: Iterable[str],
    noise_conditions: dict[str, str],
    num_cases: int = 20,
) -> pd.DataFrame:
    rows = []
    for s in build_scenarios(num_cases):
        for level in levels:
            for noise_label, noise_text in noise_conditions.items():
                prompt_id = f"{s.case_id}_{level}_{noise_label}"
                rows.append(
                    {
                        "prompt_id": prompt_id,
                        "case_id": s.case_id,
                        "level": level,
                        "noise_label": noise_label,
                        "noise_text": noise_text,
                        "stair_width_cm": s.stair_width_cm,
                        "landing_depth_cm": s.landing_depth_cm,
                        "wheelchair_width_cm": s.wheelchair_width_cm,
                        "wheelchair_length_cm": s.wheelchair_length_cm,
                        "turn_radius_cm": s.turn_radius_cm,
                        "clearance_margin_cm": s.clearance_margin_cm,
                        "criticality": s.criticality,
                        "reference_judgment": s.reference_judgment,
                        "prompt": render_prompt(s, level, noise_text),
                    }
                )
    return pd.DataFrame(rows)
