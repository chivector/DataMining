from __future__ import annotations

import argparse
import sys
import threading
import time
from concurrent.futures import FIRST_COMPLETED, Future, ThreadPoolExecutor, wait
from datetime import datetime
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from spatial_llm_mining.experiment import (
    collection_plan,
    response_key_set,
    response_record,
)
from spatial_llm_mining.io_utils import ensure_parent, load_yaml, project_path
from spatial_llm_mining.providers import build_provider


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Collect model responses for the multi-strategy experiment.")
    parser.add_argument(
        "--provider",
        default="df",
        choices=["mock", "df", "openai", "anthropic", "deepseek"],
    )
    parser.add_argument(
        "--models",
        default=None,
        help="Comma-separated model names. Defaults to config df_models for DF and mock_models for mock.",
    )
    parser.add_argument("--repeats", type=int, default=3)
    parser.add_argument(
        "--repeat-mode",
        choices=["copy", "api"],
        default="copy",
        help=(
            "copy makes one API call per provider/model/prompt_uid and writes the "
            "same response into all missing repeat rows; api calls each repeat separately."
        ),
    )
    parser.add_argument("--input", default=str(project_path("data", "experiment_prompts.csv")))
    parser.add_argument(
        "--output",
        default=str(project_path("data", "raw", "model_responses_experiment.csv")),
    )
    parser.add_argument(
        "--resume",
        dest="resume",
        action="store_true",
        default=True,
        help="Skip existing (provider, model, repeat, prompt_uid) rows. Enabled by default.",
    )
    parser.add_argument(
        "--no-resume",
        dest="resume",
        action="store_false",
        help="Ignore existing output rows and collect the full plan again.",
    )
    parser.add_argument("--limit", type=int, default=None, help="Cap the number of new calls.")
    parser.add_argument("--on-error", default="skip", choices=["skip", "abort"])
    parser.add_argument("--flush-every", type=int, default=25)
    parser.add_argument(
        "--workers",
        type=int,
        default=1,
        help="Number of concurrent API calls. Keep low if the gateway rate-limits.",
    )
    parser.add_argument(
        "--schedule",
        choices=["interleaved", "sequential"],
        default="interleaved",
        help="interleaved balances early partial data across models/repeats/strategies; sequential keeps model-major order.",
    )
    parser.add_argument(
        "--log-every",
        type=int,
        default=10,
        help="Print a detailed progress line every N calls. Use 0 to disable periodic detail logs.",
    )
    return parser.parse_args()


_THREAD_LOCAL = threading.local()


def _models_from_config(provider_name: str, raw: str | None, config: dict) -> list[str]:
    if raw:
        return [m.strip() for m in raw.split(",") if m.strip()]
    if provider_name == "mock":
        return list(config["mock_models"])
    if provider_name == "df" and config.get("df_models"):
        return list(config["df_models"])
    raise SystemExit("--models is required for this provider")


def _load_existing(output_path: Path, resume: bool) -> tuple[pd.DataFrame, set[tuple[str, str, int, str]]]:
    if not resume or not output_path.exists():
        return pd.DataFrame(), set()
    existing = pd.read_csv(output_path)
    return existing, response_key_set(existing)


def _write_combined(output_path: Path, existing: pd.DataFrame, rows: list[dict]) -> None:
    new_df = pd.DataFrame(rows)
    combined = pd.concat([existing, new_df], ignore_index=True) if not existing.empty else new_df
    combined.to_csv(output_path, index=False, encoding="utf-8-sig")


def _format_duration(seconds: float) -> str:
    seconds = max(0, int(seconds))
    hours, remainder = divmod(seconds, 3600)
    minutes, secs = divmod(remainder, 60)
    if hours:
        return f"{hours:d}h{minutes:02d}m{secs:02d}s"
    if minutes:
        return f"{minutes:d}m{secs:02d}s"
    return f"{secs:d}s"


def _emit_progress(iterator: object, message: str) -> None:
    writer = getattr(iterator, "write", None)
    if callable(writer):
        writer(message)
    else:
        print(message, flush=True)


def _strategy_counts(prompts: pd.DataFrame) -> str:
    if "strategy" not in prompts.columns:
        return "unknown"
    counts = prompts["strategy"].value_counts(sort=False)
    return ", ".join(f"{strategy}={count}" for strategy, count in counts.items())


def _interleave_plan(
    plan: list[tuple[str, int, pd.Series, list[int]]],
) -> list[tuple[str, int, pd.Series, list[int]]]:
    buckets: dict[tuple[str, int, str], list[tuple[str, int, pd.Series, list[int]]]] = {}
    order: list[tuple[str, int, str]] = []
    for item in plan:
        model, repeat, prompt_row, _target_repeats = item
        key = (model, repeat, str(prompt_row.get("strategy", "")))
        if key not in buckets:
            buckets[key] = []
            order.append(key)
        buckets[key].append(item)

    interleaved: list[tuple[str, int, pd.Series, list[int]]] = []
    while buckets:
        for key in list(order):
            bucket = buckets.get(key)
            if not bucket:
                if key in buckets:
                    del buckets[key]
                order.remove(key)
                continue
            interleaved.append(bucket.pop(0))
            if not bucket:
                del buckets[key]
                order.remove(key)
    return interleaved


def _thread_provider(provider_name: str):
    provider = getattr(_THREAD_LOCAL, "provider", None)
    provider_for = getattr(_THREAD_LOCAL, "provider_for", None)
    if provider is None or provider_for != provider_name:
        provider = build_provider(provider_name)
        _THREAD_LOCAL.provider = provider
        _THREAD_LOCAL.provider_for = provider_name
    return provider


def _copy_response_row(source_row: dict, target_repeat: int, source_repeat: int) -> dict:
    row = dict(source_row)
    row["repeat"] = target_repeat
    row["latency_seconds"] = 0.0
    row["repeat_mode"] = "copy"
    row["repeat_source"] = source_repeat
    return row


def _existing_success_sources(existing: pd.DataFrame) -> dict[tuple[str, str, str], dict]:
    if existing.empty or not {"provider", "model", "prompt_uid", "repeat", "status"}.issubset(existing.columns):
        return {}
    sources: dict[tuple[str, str, str], dict] = {}
    for _, row in existing.iterrows():
        if str(row["status"]) != "success":
            continue
        key = (str(row["provider"]), str(row["model"]), str(row["prompt_uid"]))
        if key not in sources:
            sources[key] = row.to_dict()
    return sources


def _collect_one(provider_name: str, model: str, repeat: int, prompt_row: pd.Series, collected_at: str) -> dict:
    provider = _thread_provider(provider_name)
    start = time.perf_counter()
    status = "success"
    error_message = ""
    try:
        response = provider.complete(prompt_row, model=model, repeat=repeat)
    except Exception as exc:  # noqa: BLE001 - provider failures are external
        status = "failed"
        error_message = str(exc)
        response = ""
    elapsed = time.perf_counter() - start
    row = response_record(
        prompt_row=prompt_row,
        provider=provider,
        provider_name=provider_name,
        model=model,
        repeat=repeat,
        collected_at=collected_at,
        response=response,
        status=status,
        error_message=error_message,
        latency_seconds=elapsed,
    )
    row["repeat_mode"] = "api"
    row["repeat_source"] = ""
    return row


def _collect_repeat_group(
    provider_name: str,
    model: str,
    source_repeat: int,
    prompt_row: pd.Series,
    collected_at: str,
    target_repeats: list[int],
    repeat_mode: str,
) -> list[dict]:
    source_row = _collect_one(provider_name, model, source_repeat, prompt_row, collected_at)
    if repeat_mode == "api":
        return [source_row]

    source_row["repeat_mode"] = "source"
    source_row["repeat_source"] = ""
    rows: list[dict] = []
    for target_repeat in target_repeats:
        if target_repeat == source_repeat:
            rows.append(source_row)
        else:
            rows.append(_copy_response_row(source_row, target_repeat, source_repeat))
    return rows


def _api_repeat_plan(
    prompts: pd.DataFrame,
    provider_name: str,
    models: list[str],
    repeats: int,
    seen: set[tuple[str, str, int, str]],
) -> list[tuple[str, int, pd.Series, list[int]]]:
    return [(model, repeat, prompt_row, [repeat]) for model, repeat, prompt_row in collection_plan(prompts, provider_name, models, repeats, seen)]


def _copy_repeat_plan(
    prompts: pd.DataFrame,
    provider_name: str,
    models: list[str],
    repeats: int,
    seen: set[tuple[str, str, int, str]],
    existing: pd.DataFrame,
) -> tuple[list[tuple[str, int, pd.Series, list[int]]], list[dict]]:
    plan: list[tuple[str, int, pd.Series, list[int]]] = []
    copied_rows: list[dict] = []
    existing_sources = _existing_success_sources(existing)
    for model in models:
        for _, prompt_row in prompts.iterrows():
            prompt_uid = str(prompt_row["prompt_uid"])
            target_repeats = [
                repeat
                for repeat in range(repeats)
                if (provider_name, model, repeat, prompt_uid) not in seen
            ]
            if not target_repeats:
                continue
            existing_source = existing_sources.get((provider_name, model, prompt_uid))
            if existing_source is not None:
                source_repeat = int(existing_source["repeat"])
                for target_repeat in target_repeats:
                    copied_row = _copy_response_row(existing_source, target_repeat, source_repeat)
                    copied_row["repeat_mode"] = "copy_existing"
                    copied_rows.append(copied_row)
                    seen.add((provider_name, model, target_repeat, prompt_uid))
                continue
            plan.append((model, min(target_repeats), prompt_row, target_repeats))
    return plan, copied_rows


def _submit_next(
    executor: ThreadPoolExecutor,
    pending: set[Future],
    plan_iter,
    provider_name: str,
    collected_at: str,
    repeat_mode: str,
) -> bool:
    try:
        model, source_repeat, prompt_row, target_repeats = next(plan_iter)
    except StopIteration:
        return False
    pending.add(
        executor.submit(
            _collect_repeat_group,
            provider_name,
            model,
            source_repeat,
            prompt_row,
            collected_at,
            target_repeats,
            repeat_mode,
        )
    )
    return True


def main() -> None:
    args = parse_args()
    config = load_yaml(project_path("config", "experiment.yml"))
    prompts = pd.read_csv(args.input)
    if "prompt_uid" not in prompts.columns:
        raise SystemExit("input prompts must include prompt_uid; run scripts/build_experiment_prompts.py first")

    models = _models_from_config(args.provider, args.models, config)
    build_provider(args.provider)

    output_path = Path(args.output)
    ensure_parent(output_path)
    existing_df, seen = _load_existing(output_path, args.resume)
    full_total = len(models) * args.repeats * len(prompts)
    copied_rows: list[dict] = []
    if args.repeat_mode == "api":
        plan = _api_repeat_plan(prompts, args.provider, models, args.repeats, seen)
    else:
        plan, copied_rows = _copy_repeat_plan(prompts, args.provider, models, args.repeats, seen, existing_df)
    remaining_rows_before_limit = len(copied_rows) + sum(len(target_repeats) for *_rest, target_repeats in plan)
    api_calls_before_limit = len(plan)
    if args.schedule == "interleaved":
        plan = _interleave_plan(plan)
    if args.limit is not None:
        plan = plan[: args.limit]
    rows_this_run = len(copied_rows) + sum(len(target_repeats) for *_rest, target_repeats in plan)

    if not plan:
        if copied_rows:
            _write_combined(output_path, existing_df, copied_rows)
            print(
                f"copied {len(copied_rows)} repeat rows from existing successes "
                f"(total {len(existing_df) + len(copied_rows)}) -> {output_path}"
            )
            return
        print(f"nothing to do (existing rows: {len(existing_df)}). output -> {output_path}")
        return

    print("experiment collection plan")
    print(f"  input: {args.input}")
    print(f"  output: {output_path}")
    print(f"  provider: {args.provider}")
    print(f"  models: {', '.join(models)}")
    print(f"  repeats: {args.repeats}")
    print(f"  repeat mode: {args.repeat_mode}")
    print(f"  prompt rows: {len(prompts)} ({_strategy_counts(prompts)})")
    print(f"  total planned rows: {full_total}")
    print(f"  existing rows loaded: {len(existing_df)}")
    print(f"  already completed by resume key: {full_total - remaining_rows_before_limit}")
    print(f"  rows copied from existing successes: {len(copied_rows)}")
    print(f"  api calls before limit: {api_calls_before_limit}")
    if args.limit is not None:
        print(f"  limit: {args.limit} new calls this run")
    print(f"  api calls this run: {len(plan)}")
    print(f"  rows this run: {rows_this_run}")
    print(f"  workers: {args.workers}")
    print(f"  schedule: {args.schedule}")
    print(f"  flush every: {args.flush_every} calls")
    print(f"  detailed log every: {args.log_every} calls")

    collected_at = datetime.now().isoformat(timespec="seconds")
    new_rows: list[dict] = list(copied_rows)
    failures = 0
    successes = sum(1 for row in copied_rows if str(row.get("status")) == "success")
    run_started = time.perf_counter()

    try:
        from tqdm import tqdm
    except ImportError:
        tqdm = None

    progress = tqdm(total=len(plan), desc=args.provider, unit="call") if tqdm else None
    workers = max(1, int(args.workers))
    executor = ThreadPoolExecutor(max_workers=workers)
    max_pending = max(workers * 2, workers)
    plan_iter = iter(plan)
    pending: set[Future] = set()
    for _ in range(min(max_pending, len(plan))):
        _submit_next(executor, pending, plan_iter, args.provider, collected_at, args.repeat_mode)
    aborted = False

    try:
        idx = 0
        while pending:
            done, pending = wait(pending, return_when=FIRST_COMPLETED)
            for future in done:
                idx += 1
                rows = future.result()
                _submit_next(executor, pending, plan_iter, args.provider, collected_at, args.repeat_mode)
                new_rows.extend(rows)
                row = rows[0]
                failed_rows = [item for item in rows if str(item["status"]) != "success"]
                successes += len(rows) - len(failed_rows)
                failures += len(failed_rows)
                target_repeats = ",".join(str(item["repeat"]) for item in rows)
                status = "failed" if failed_rows else "success"
                if failed_rows:
                    print(
                        f"[{idx}/{len(plan)}] {args.provider}/{row['model']} repeats={target_repeats} "
                        f"{row['prompt_uid']} FAILED: {row['error_message']}",
                        file=sys.stderr,
                    )

                if progress:
                    progress.update(1)
                    progress.set_postfix(
                        {
                            "workers": workers,
                            "model": row["model"],
                            "repeats": target_repeats,
                            "strategy": row.get("strategy", ""),
                            "ok": successes,
                            "fail": failures,
                        }
                    )

                should_log = args.log_every > 0 and (idx == 1 or idx % args.log_every == 0 or idx == len(plan))
                if should_log:
                    elapsed_total = time.perf_counter() - run_started
                    avg = elapsed_total / max(1, idx)
                    eta = avg * (len(plan) - idx)
                    _emit_progress(
                        progress,
                        (
                            f"progress {idx}/{len(plan)} "
                            f"({idx / len(plan):.1%}) | "
                            f"workers={workers} | "
                            f"finished={args.provider}/{row['model']} repeats={target_repeats} "
                            f"strategy={row.get('strategy', 'unknown')} "
                            f"level={row.get('level', 'unknown')} "
                            f"noise={row.get('noise_label', 'unknown')} "
                            f"prompt_uid={row.get('prompt_uid', row.get('prompt_id', 'unknown'))} | "
                            f"last={float(row['latency_seconds']):.2f}s avg={avg:.2f}s/api-call "
                            f"elapsed={_format_duration(elapsed_total)} eta={_format_duration(eta)} | "
                            f"success={successes} failed={failures}"
                        ),
                    )

                if idx % max(1, args.flush_every) == 0:
                    _write_combined(output_path, existing_df, new_rows)
                    _emit_progress(
                        progress,
                        f"flushed {len(new_rows)} new rows (+ {len(existing_df)} existing) -> {output_path}",
                    )

                if status == "failed" and args.on_error == "abort":
                    _write_combined(output_path, existing_df, new_rows)
                    for pending_future in pending:
                        pending_future.cancel()
                    aborted = True
                    executor.shutdown(wait=False, cancel_futures=True)
                    raise SystemExit(f"aborted after provider failure; partial output -> {output_path}")
    except KeyboardInterrupt:
        _write_combined(output_path, existing_df, new_rows)
        for pending_future in pending:
            pending_future.cancel()
        aborted = True
        executor.shutdown(wait=False, cancel_futures=True)
        raise SystemExit(f"interrupted; wrote {len(new_rows)} new rows -> {output_path}")
    finally:
        if progress:
            progress.close()
        if not aborted:
            executor.shutdown(wait=True, cancel_futures=False)

    _write_combined(output_path, existing_df, new_rows)
    total_rows = len(existing_df) + len(new_rows)
    elapsed_total = time.perf_counter() - run_started
    print(
        f"wrote {len(new_rows)} new responses "
        f"(total {total_rows}, api calls {idx}, successes {successes}, failures {failures}, "
        f"elapsed {_format_duration(elapsed_total)}) -> {output_path}"
    )


if __name__ == "__main__":
    main()
