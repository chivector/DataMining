from __future__ import annotations

from collections.abc import Callable
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


@dataclass(frozen=True)
class PromptStrategy:
    name: str
    description: str


def stable_int(*values: object, modulo: int = 10_000) -> int:
    text = "|".join(str(v) for v in values)
    return int(sha256(text.encode("utf-8")).hexdigest()[:12], 16) % modulo


def _classify_margin(
    stair_width_cm: int,
    landing_depth_cm: int,
    wheelchair_width_cm: int,
    turn_radius_cm: int,
) -> tuple[int, str, str]:
    side_clearance = stair_width_cm - wheelchair_width_cm
    turn_clearance = landing_depth_cm - turn_radius_cm
    margin = min(side_clearance, turn_clearance)
    if margin >= 10:
        return margin, "can_pass", "wide"
    if margin >= 3:
        return margin, "can_pass", "borderline"
    if margin >= -4:
        return margin, "cannot_pass", "borderline"
    return margin, "cannot_pass", "narrow"


def _scenario(
    idx: int,
    stair_width_cm: int,
    landing_depth_cm: int,
    wheelchair_width_cm: int,
    wheelchair_length_cm: int,
    turn_radius_cm: int,
) -> Scenario:
    margin, judgment, criticality = _classify_margin(
        stair_width_cm,
        landing_depth_cm,
        wheelchair_width_cm,
        turn_radius_cm,
    )
    return Scenario(
        case_id=f"C{idx + 1:03d}",
        stair_width_cm=stair_width_cm,
        landing_depth_cm=landing_depth_cm,
        wheelchair_width_cm=wheelchair_width_cm,
        wheelchair_length_cm=wheelchair_length_cm,
        turn_radius_cm=turn_radius_cm,
        clearance_margin_cm=margin,
        reference_judgment=judgment,
        criticality=criticality,
    )


def _baseline_hash_scenarios(num_cases: int) -> list[Scenario]:
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
        scenarios.append(_scenario(idx, stair_width, landing_depth, chair_width, chair_length, turn_radius))
    return scenarios


FACTOR_RANGES = {
    "stair_width_cm": (78, 116),
    "landing_depth_cm": (80, 136),
    "wheelchair_width_cm": (58, 82),
    "wheelchair_length_cm": (96, 136),
    "turn_radius_cm": (72, 122),
}


def _from_unit(low: int, high: int, unit: float) -> int:
    unit = max(0.0, min(1.0, unit))
    return round(low + unit * (high - low))


def _levels(low: int, high: int, count: int) -> list[int]:
    if count <= 1:
        return [round((low + high) / 2)]
    return [round(low + (high - low) * idx / (count - 1)) for idx in range(count)]


def _vector(values: tuple[int, int, int, int, int]) -> tuple[float, ...]:
    keys = [
        "stair_width_cm",
        "landing_depth_cm",
        "wheelchair_width_cm",
        "wheelchair_length_cm",
        "turn_radius_cm",
    ]
    return tuple((value - FACTOR_RANGES[key][0]) / (FACTOR_RANGES[key][1] - FACTOR_RANGES[key][0]) for key, value in zip(keys, values))


def _distance_sq(a: tuple[float, ...], b: tuple[float, ...]) -> float:
    return sum((left - right) ** 2 for left, right in zip(a, b))


def _halton(index: int, base: int) -> float:
    result = 0.0
    fraction = 1.0 / base
    current = index
    while current > 0:
        result += fraction * (current % base)
        current //= base
        fraction /= base
    return result


def _build_scenarios_from_values(values: list[tuple[int, int, int, int, int]], num_cases: int) -> list[Scenario]:
    scenarios: list[Scenario] = []
    for idx, dims in enumerate(values[:num_cases]):
        scenarios.append(_scenario(idx, *dims))
    return scenarios


def _latin_hypercube_coverage(num_cases: int) -> list[Scenario]:
    ranges = list(FACTOR_RANGES.values())
    steps = [7, 11, 13, 17, 19]
    offsets = [0, 3, 6, 9, 12]
    values = []
    for idx in range(num_cases):
        dims = []
        for factor_idx, (low, high) in enumerate(ranges):
            slot = (idx * steps[factor_idx] + offsets[factor_idx]) % num_cases
            dims.append(_from_unit(low, high, (slot + 0.5) / num_cases))
        values.append(tuple(dims))
    return _build_scenarios_from_values(values, num_cases)


def _halton_space_filling(num_cases: int) -> list[Scenario]:
    ranges = list(FACTOR_RANGES.values())
    bases = [2, 3, 5, 7, 11]
    values = []
    for idx in range(num_cases):
        dims = [_from_unit(low, high, _halton(idx + 1, base)) for base, (low, high) in zip(bases, ranges)]
        values.append(tuple(dims))
    return _build_scenarios_from_values(values, num_cases)


def _orthogonal_array_interactions(num_cases: int) -> list[Scenario]:
    width_levels = _levels(80, 112, 5)
    depth_levels = _levels(84, 132, 5)
    chair_width_levels = _levels(60, 84, 5)
    chair_length_levels = _levels(96, 136, 5)
    radius_levels = _levels(74, 122, 5)
    rows = [(a, b) for a in range(5) for b in range(5) if a != b]
    values = []
    for idx in range(num_cases):
        a, b = rows[idx % len(rows)]
        levels = [a, b, (a + b) % 5, (a + 2 * b) % 5, (2 * a + b) % 5]
        values.append(
            (
                width_levels[levels[0]],
                depth_levels[levels[1]],
                chair_width_levels[levels[2]],
                chair_length_levels[levels[3]],
                radius_levels[levels[4]],
            )
        )
    return _build_scenarios_from_values(values, num_cases)


def _fractional_factorial_effects(num_cases: int) -> list[Scenario]:
    lows = [82, 88, 62, 100, 78]
    highs = [110, 128, 80, 134, 118]
    values = []
    for run in range(16):
        signs = [1 if run & (1 << bit) else -1 for bit in range(4)]
        signs.append(signs[0] * signs[1] * signs[2] * signs[3])
        values.append(tuple(high if sign > 0 else low for low, high, sign in zip(lows, highs, signs)))
    values.extend(
        [
            (96, 108, 70, 116, 98),
            (90, 98, 74, 116, 104),
            (104, 94, 68, 124, 100),
            (88, 112, 82, 108, 100),
        ]
    )
    while len(values) < num_cases:
        values.extend(values[: num_cases - len(values)])
    return _build_scenarios_from_values(values, num_cases)


def _d_optimal_balanced_subset(num_cases: int) -> list[Scenario]:
    factor_levels = [
        [78, 90, 102, 114],
        [82, 98, 114, 130],
        [60, 68, 76, 84],
        [98, 112, 126, 140],
        [74, 90, 106, 122],
    ]
    candidates = [
        (w, d, cw, cl, r)
        for w in factor_levels[0]
        for d in factor_levels[1]
        for cw in factor_levels[2]
        for cl in factor_levels[3]
        for r in factor_levels[4]
    ]
    vectors = {candidate: _vector(candidate) for candidate in candidates}
    labels = {
        candidate: _classify_margin(candidate[0], candidate[1], candidate[2], candidate[4])[1]
        for candidate in candidates
    }
    selected: list[tuple[int, int, int, int, int]] = []
    label_target = {"can_pass": num_cases // 2, "cannot_pass": num_cases - num_cases // 2}
    counts = {"can_pass": 0, "cannot_pass": 0}
    first_can = max((c for c in candidates if labels[c] == "can_pass"), key=lambda c: _classify_margin(c[0], c[1], c[2], c[4])[0])
    first_cannot = min((c for c in candidates if labels[c] == "cannot_pass"), key=lambda c: _classify_margin(c[0], c[1], c[2], c[4])[0])
    for first in (first_can, first_cannot):
        if len(selected) < num_cases:
            selected.append(first)
            counts[labels[first]] += 1

    while len(selected) < num_cases:
        allowed_labels = [label for label, count in counts.items() if count < label_target[label]]
        pool = [candidate for candidate in candidates if candidate not in selected and labels[candidate] in allowed_labels]
        if not pool:
            pool = [candidate for candidate in candidates if candidate not in selected]

        def score(candidate: tuple[int, int, int, int, int]) -> tuple[float, int, tuple[int, int, int, int, int]]:
            min_dist = min(_distance_sq(vectors[candidate], vectors[chosen]) for chosen in selected)
            margin = abs(_classify_margin(candidate[0], candidate[1], candidate[2], candidate[4])[0])
            return min_dist, margin, candidate

        best = max(pool, key=score)
        selected.append(best)
        counts[labels[best]] += 1
    return _build_scenarios_from_values(selected, num_cases)


def _dimensionless_ratio_design(num_cases: int) -> list[Scenario]:
    ratio_specs = [
        (0.98, 1.18, 0.70),
        (1.18, 0.96, 0.76),
        (1.16, 1.14, 0.84),
        (1.30, 1.24, 0.92),
        (1.05, 1.04, 1.00),
        (1.02, 1.16, 0.88),
        (1.22, 1.02, 0.78),
        (1.08, 1.08, 0.86),
        (1.32, 0.98, 0.94),
        (1.14, 1.20, 0.72),
    ]
    chair_widths = [60, 64, 68, 72, 76]
    chair_lengths = [100, 108, 116, 124]
    values = []
    for idx in range(num_cases):
        width_ratio, depth_ratio, radius_length_ratio = ratio_specs[idx % len(ratio_specs)]
        chair_width = chair_widths[idx % len(chair_widths)]
        chair_length = chair_lengths[(idx // len(chair_widths)) % len(chair_lengths)]
        turn_radius = round(chair_length * radius_length_ratio)
        stair_width = round(chair_width * width_ratio)
        landing_depth = round(turn_radius * depth_ratio)
        values.append((stair_width, landing_depth, chair_width, chair_length, turn_radius))
    return _build_scenarios_from_values(values, num_cases)


def _metamorphic_counterfactual_pairs(num_cases: int) -> list[Scenario]:
    values = []
    pair_specs = [
        ("width", 1, 3),
        ("depth", 2, 4),
        ("width", -5, -3),
        ("depth", 9, 11),
        ("width", 2, 4),
        ("depth", -4, -2),
        ("width", 8, 10),
        ("depth", 0, 3),
        ("width", -6, -4),
        ("depth", 10, 12),
    ]
    for pair_idx, (active_dim, before_margin, after_margin) in enumerate(pair_specs):
        chair_width = 66 + (pair_idx % 5) * 2
        chair_length = 104 + (pair_idx % 4) * 6
        turn_radius = 82 + (pair_idx % 5) * 4
        if active_dim == "width":
            values.append((chair_width + before_margin, turn_radius + 16, chair_width, chair_length, turn_radius))
            values.append((chair_width + after_margin, turn_radius + 16, chair_width, chair_length, turn_radius))
        else:
            values.append((chair_width + 16, turn_radius + before_margin, chair_width, chair_length, turn_radius))
            values.append((chair_width + 16, turn_radius + after_margin, chair_width, chair_length, turn_radius))
    while len(values) < num_cases:
        values.extend(values[: num_cases - len(values)])
    return _build_scenarios_from_values(values, num_cases)


def _constraint_boundary_solver(num_cases: int) -> list[Scenario]:
    target_margins = [-8, -5, -4, -3, 0, 2, 3, 4, 9, 10, 11, 14, 18, -6, -2, 1, 5, 8, 12, 16]
    values = []
    for idx in range(num_cases):
        target = target_margins[idx % len(target_margins)]
        active_width = idx % 2 == 0
        chair_width = 62 + (idx % 6) * 3
        chair_length = 100 + (idx % 5) * 7
        turn_radius = 78 + (idx % 7) * 5
        slack = 6 + (idx % 4) * 3
        if active_width:
            values.append((chair_width + target, turn_radius + target + slack, chair_width, chair_length, turn_radius))
        else:
            values.append((chair_width + target + slack, turn_radius + target, chair_width, chair_length, turn_radius))
    return _build_scenarios_from_values(values, num_cases)


def _conflicting_cue_adversarial(num_cases: int) -> list[Scenario]:
    values = []
    patterns = [
        (24, -8),
        (20, -4),
        (16, 2),
        (-8, 24),
        (-4, 20),
        (2, 16),
        (12, 3),
        (3, 12),
        (28, -12),
        (-12, 28),
    ]
    for idx in range(num_cases):
        side_margin, turn_margin = patterns[idx % len(patterns)]
        chair_width = 64 + (idx % 5) * 3
        chair_length = 102 + (idx % 4) * 8
        turn_radius = 80 + (idx % 6) * 5
        values.append((chair_width + side_margin, turn_radius + turn_margin, chair_width, chair_length, turn_radius))
    return _build_scenarios_from_values(values, num_cases)


def _real_world_archetype_matrix(num_cases: int) -> list[Scenario]:
    archetypes = [
        (84, 88, 68, 108, 86),
        (92, 104, 70, 112, 90),
        (108, 122, 72, 118, 96),
        (98, 112, 74, 122, 100),
        (116, 132, 76, 126, 104),
    ]
    variations = [
        (-10, -12, 4, -4, 6),
        (-4, -6, 2, 0, 4),
        (2, 4, 0, 4, 0),
        (8, 10, -2, 8, -2),
    ]
    values = []
    for idx in range(num_cases):
        base = archetypes[idx % len(archetypes)]
        delta = variations[(idx // len(archetypes)) % len(variations)]
        values.append(tuple(base_value + shift for base_value, shift in zip(base, delta)))
    return _build_scenarios_from_values(values, num_cases)


def _rounding_threshold_ladder(num_cases: int) -> list[Scenario]:
    anchors = [80, 90, 100, 110]
    offsets = [-2, -1, 0, 1, 2]
    target_margins = [-5, -4, -3, 2, 3, 4, 9, 10, 11, -1]
    values = []
    for idx in range(num_cases):
        anchor = anchors[(idx // len(offsets)) % len(anchors)]
        offset = offsets[idx % len(offsets)]
        target_margin = target_margins[idx % len(target_margins)]
        stair_anchor = anchor + offset
        depth_anchor = anchor + offset
        chair_length = anchor + 18 + ((idx // 3) % 6) * 3
        if idx % 2 == 0:
            stair_width = stair_anchor
            chair_width = stair_width - target_margin
            turn_radius = anchor - 8 + ((idx // 2) % 5)
            landing_depth = turn_radius + max(12, target_margin + 8)
        else:
            landing_depth = depth_anchor
            turn_radius = landing_depth - target_margin
            chair_width = anchor - 20 + (idx % 3)
            stair_width = chair_width + max(12, target_margin + 8)
        values.append((stair_width, landing_depth, chair_width, chair_length, turn_radius))
    return _build_scenarios_from_values(values, num_cases)


_SCENARIO_BUILDERS: dict[str, Callable[[int], list[Scenario]]] = {
    "hash_baseline": _baseline_hash_scenarios,
    "latin_hypercube_coverage": _latin_hypercube_coverage,
    "halton_space_filling": _halton_space_filling,
    "orthogonal_array_interactions": _orthogonal_array_interactions,
    "fractional_factorial_effects": _fractional_factorial_effects,
    "d_optimal_balanced_subset": _d_optimal_balanced_subset,
    "dimensionless_ratio_design": _dimensionless_ratio_design,
    "metamorphic_counterfactual_pairs": _metamorphic_counterfactual_pairs,
    "constraint_boundary_solver": _constraint_boundary_solver,
    "conflicting_cue_adversarial": _conflicting_cue_adversarial,
    "real_world_archetype_matrix": _real_world_archetype_matrix,
    "rounding_threshold_ladder": _rounding_threshold_ladder,
}


ADDITIONAL_PROMPT_STRATEGIES: tuple[PromptStrategy, ...] = (
    PromptStrategy("latin_hypercube_coverage", "拉丁超立方覆盖五个几何变量，使每个变量区间都被均匀访问。"),
    PromptStrategy("halton_space_filling", "使用 Halton 低差异序列做准蒙特卡洛空间填充采样。"),
    PromptStrategy("orthogonal_array_interactions", "用正交表覆盖几何因素主效应和二阶交互。"),
    PromptStrategy("fractional_factorial_effects", "用分数因子实验设计分析尺寸因素高低水平效应。"),
    PromptStrategy("d_optimal_balanced_subset", "从候选池中贪心选择最大距离且标签平衡的近似 D-optimal 子集。"),
    PromptStrategy("dimensionless_ratio_design", "用 W/w、D/R、R/L 等无量纲比例构造相对尺度样本。"),
    PromptStrategy("metamorphic_counterfactual_pairs", "每两条组成反事实对，只微调一个关键参数 1-3cm。"),
    PromptStrategy("constraint_boundary_solver", "反向求解目标余量，让样本精确落在关键判定阈值附近。"),
    PromptStrategy("conflicting_cue_adversarial", "构造宽度线索和转弯半径线索相互冲突的对抗样本。"),
    PromptStrategy("real_world_archetype_matrix", "按旧住宅楼、教学楼、医院、办公楼、电梯厅等现实原型组织尺寸矩阵。"),
    PromptStrategy("rounding_threshold_ladder", "围绕 80/90/100/110cm 常见整数和阈值边界构造阶梯样本。"),
)


def list_prompt_strategies(include_baseline: bool = True) -> list[PromptStrategy]:
    strategies = list(ADDITIONAL_PROMPT_STRATEGIES)
    if include_baseline:
        strategies.insert(0, PromptStrategy("hash_baseline", "原始哈希式确定性构造。"))
    return strategies


def build_scenarios(num_cases: int = 20, strategy: str = "hash_baseline") -> list[Scenario]:
    try:
        builder = _SCENARIO_BUILDERS[strategy]
    except KeyError as exc:
        available = ", ".join(sorted(_SCENARIO_BUILDERS))
        raise ValueError(f"Unknown scenario strategy: {strategy}. Available: {available}") from exc
    return builder(num_cases)


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
    strategy: str = "hash_baseline",
) -> pd.DataFrame:
    rows = []
    for s in build_scenarios(num_cases, strategy=strategy):
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
