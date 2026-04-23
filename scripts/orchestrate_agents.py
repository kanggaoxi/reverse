#!/usr/bin/env python3
"""Run multiple CLI-driven agent workers against isolated git worktrees.

This script is aimed at black-box exploration workflows such as reverse
engineering a weakly documented DSL. Each worker gets:

- its own git worktree
- its own prompt / scope
- its own agent session id, when the CLI exposes one
- per-agent logs, state, and last-message files

The orchestration model is intentionally simple:

1. Start one agent CLI process per agent.
2. Stream and persist its JSONL events.
3. When a turn exits, decide whether to stop, retry, or resume the same
   session with a follow-up "nudge" prompt.
4. Optionally interrupt and resume sessions that appear stalled.

Example:
    python3 scripts/orchestrate_agents.py \
        --config scripts/swft_agents.example.json
"""

from __future__ import annotations

import argparse
import json
import os
import queue
import shlex
import signal
import subprocess
import sys
import threading
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any


DEFAULT_DONE_MARKER = "DONE:"
DEFAULT_JUDGE_DONE_MARKER = "JUDGE_JSON:"


def now_ts() -> float:
    return time.time()


def format_age(seconds: float) -> str:
    seconds = max(0, int(seconds))
    minutes, secs = divmod(seconds, 60)
    hours, minutes = divmod(minutes, 60)
    if hours:
        return f"{hours}h{minutes:02d}m{secs:02d}s"
    if minutes:
        return f"{minutes}m{secs:02d}s"
    return f"{secs}s"


def ensure_dir(path: Path) -> Path:
    path.mkdir(parents=True, exist_ok=True)
    return path


def load_json(path: Path) -> dict[str, Any]:
    with path.open("r", encoding="utf-8") as f:
        return json.load(f)


def dump_json(path: Path, data: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    with tmp.open("w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False, sort_keys=True)
    tmp.replace(path)


def run_checked(cmd: list[str], cwd: Path) -> subprocess.CompletedProcess[str]:
    return subprocess.run(cmd, cwd=cwd, check=True, text=True, capture_output=True)


def git_branch_exists(repo_root: Path, branch: str) -> bool:
    result = subprocess.run(
        ["git", "show-ref", "--verify", "--quiet", f"refs/heads/{branch}"],
        cwd=repo_root,
        text=True,
        capture_output=True,
    )
    return result.returncode == 0


def worktree_registered(repo_root: Path, worktree: Path) -> bool:
    result = run_checked(["git", "worktree", "list", "--porcelain"], cwd=repo_root)
    normalized = str(worktree.resolve())
    for line in result.stdout.splitlines():
        if line.startswith("worktree ") and line[len("worktree ") :] == normalized:
            return True
    return False


def ensure_worktree(repo_root: Path, worktree: Path, branch: str, base_branch: str) -> None:
    if worktree_registered(repo_root, worktree):
        return

    if worktree.exists() and any(worktree.iterdir()):
        raise RuntimeError(
            f"Refusing to attach worktree at non-empty path that is not already "
            f"registered: {worktree}"
        )

    worktree.parent.mkdir(parents=True, exist_ok=True)

    if git_branch_exists(repo_root, branch):
        cmd = ["git", "worktree", "add", str(worktree), branch]
    else:
        cmd = ["git", "worktree", "add", str(worktree), "-b", branch, base_branch]
    run_checked(cmd, cwd=repo_root)


def resolve_path(base: Path, value: str | None) -> Path | None:
    if value is None:
        return None
    path = Path(value)
    if path.is_absolute():
        return path
    return (base / path).resolve()


def read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8") if path.exists() else ""


def clip_text(text: str, limit: int) -> str:
    if len(text) <= limit:
        return text
    return text[:limit] + "\n...[truncated]..."


def cli_backend_name(agent_cli: str) -> str:
    return Path(agent_cli).name.lower()


def extract_opencode_text(payload: str) -> str:
    chunks: list[str] = []
    for raw_line in payload.splitlines():
        line = raw_line.strip()
        if not line:
            continue
        try:
            event = json.loads(line)
        except json.JSONDecodeError:
            continue
        event_type = str(event.get("type", ""))
        if event_type == "text":
            part = event.get("part")
            if not isinstance(part, dict):
                continue
            text = part.get("text")
            if isinstance(text, str):
                chunks.append(text)
        elif event_type == "item.completed":
            item = event.get("item")
            if isinstance(item, dict) and item.get("type") == "agent_message":
                text = item.get("text")
                if isinstance(text, str) and text.strip():
                    chunks.append(text)
    return "".join(chunks)


@dataclass
class AgentSpec:
    name: str
    branch: str
    worktree: Path
    base_branch: str
    prompt: str
    status_file: str | None = None
    max_rounds: int = 4
    max_retries: int = 2
    extra_agent_args: list[str] = field(default_factory=list)
    done_marker: str = DEFAULT_DONE_MARKER
    interrupt_stalled: bool = False
    judge_prompt: str | None = None


@dataclass
class AgentRuntime:
    spec: AgentSpec
    state_dir: Path
    agent_cli: str
    model: str | None
    full_auto: bool
    json_output: bool
    common_prompt: str
    nudge_prompt: str
    recovery_prompt: str
    stall_prompt: str
    global_extra_args: list[str]
    require_judge_approval: bool
    initial_command_template: list[str] | None
    resume_command_template: list[str] | None
    resume_requires_session: bool
    state_path: Path = field(init=False)
    log_path: Path = field(init=False)
    last_message_path: Path = field(init=False)
    event_queue: "queue.Queue[str]" = field(init=False, default_factory=queue.Queue)
    process: subprocess.Popen[str] | None = field(init=False, default=None)
    reader_thread: threading.Thread | None = field(init=False, default=None)
    session_id: str | None = field(init=False, default=None)
    round_index: int = field(init=False, default=0)
    retry_count: int = field(init=False, default=0)
    last_event_ts: float = field(init=False, default_factory=now_ts)
    last_spawn_ts: float = field(init=False, default_factory=now_ts)
    last_status: str = field(init=False, default="pending")
    last_exit_code: int | None = field(init=False, default=None)
    pending_prompt: str | None = field(init=False, default=None)
    done: bool = field(init=False, default=False)
    failures: int = field(init=False, default=0)
    raw_event_count: int = field(init=False, default=0)
    json_event_count: int = field(init=False, default=0)
    stall_warnings: int = field(init=False, default=0)
    judge_runs: int = field(init=False, default=0)
    proposed_done: bool = field(init=False, default=False)

    def __post_init__(self) -> None:
        self.state_path = self.state_dir / f"{self.spec.name}.state.json"
        self.log_path = self.state_dir / f"{self.spec.name}.events.log"
        self.last_message_path = self.state_dir / f"{self.spec.name}.last.txt"
        self._load_state()

    def _load_state(self) -> None:
        if not self.state_path.exists():
            return
        data = load_json(self.state_path)
        self.session_id = data.get("session_id")
        self.round_index = int(data.get("round_index", 0))
        self.retry_count = int(data.get("retry_count", 0))
        self.last_status = str(data.get("last_status", "pending"))
        self.last_exit_code = data.get("last_exit_code")
        self.done = bool(data.get("done", False))
        self.proposed_done = bool(data.get("proposed_done", False))
        self.failures = int(data.get("failures", 0))
        self.last_event_ts = float(data.get("last_event_ts", now_ts()))
        self.last_spawn_ts = float(data.get("last_spawn_ts", now_ts()))
        self.raw_event_count = int(data.get("raw_event_count", 0))
        self.json_event_count = int(data.get("json_event_count", 0))
        self.stall_warnings = int(data.get("stall_warnings", 0))
        self.judge_runs = int(data.get("judge_runs", 0))
        self.pending_prompt = data.get("pending_prompt")

    def save_state(self) -> None:
        dump_json(
            self.state_path,
            {
                "name": self.spec.name,
                "branch": self.spec.branch,
                "worktree": str(self.spec.worktree),
                "session_id": self.session_id,
                "round_index": self.round_index,
                "retry_count": self.retry_count,
                "last_status": self.last_status,
                "last_exit_code": self.last_exit_code,
                "done": self.done,
                "proposed_done": self.proposed_done,
                "failures": self.failures,
                "last_event_ts": self.last_event_ts,
                "last_spawn_ts": self.last_spawn_ts,
                "raw_event_count": self.raw_event_count,
                "json_event_count": self.json_event_count,
                "stall_warnings": self.stall_warnings,
                "judge_runs": self.judge_runs,
                "pending_prompt": self.pending_prompt,
                "last_message_path": str(self.last_message_path),
                "log_path": str(self.log_path),
            },
        )

    def compose_initial_prompt(self) -> str:
        sections = [self.common_prompt.strip(), self.spec.prompt.strip()]
        if self.spec.status_file:
            sections.append(
                "Record concrete findings in "
                f"`{self.spec.status_file}` or the notes adjacent to it."
            )
        sections.append(
            "When your assigned scope is exhausted, begin the final answer with "
            f"`{self.spec.done_marker} ...`."
        )
        return "\n\n".join(part for part in sections if part)

    def compose_resume_prompt(self, template: str) -> str:
        status_hint = self.spec.status_file or "your assigned notes and result files"
        last_message = read_text(self.last_message_path).strip()
        if last_message:
            last_message = last_message[:1200]
        prompt = template.format(
            agent_name=self.spec.name,
            branch=self.spec.branch,
            worktree=self.spec.worktree,
            round_index=self.round_index + 1,
            status_file=status_hint,
            last_message=last_message,
            done_marker=self.spec.done_marker,
        )
        return prompt.strip()

    def append_log(self, line: str) -> None:
        ensure_dir(self.log_path.parent)
        with self.log_path.open("a", encoding="utf-8") as f:
            f.write(line)
            if not line.endswith("\n"):
                f.write("\n")

    def _reader(self) -> None:
        assert self.process is not None
        assert self.process.stdout is not None
        for line in self.process.stdout:
            self.event_queue.put(line.rstrip("\n"))

    def _base_exec_args(self) -> list[str]:
        if cli_backend_name(self.agent_cli) == "opencode":
            args = [self.agent_cli, "run"]
            if self.full_auto:
                args.append("--dangerously-skip-permissions")
            if self.json_output:
                args.extend(["--format", "json"])
            if self.model:
                args.extend(["--model", self.model])
        else:
            args = [self.agent_cli, "exec"]
            if self.full_auto:
                args.append("--full-auto")
            if self.json_output:
                args.append("--json")
            if self.model:
                args.extend(["-m", self.model])
        args.extend(self.global_extra_args)
        return args

    def _render_command_template(self, template: list[str], prompt: str, *, resume: bool) -> list[str]:
        values = {
            "agent_cli": self.agent_cli,
            "model": self.model or "",
            "prompt": prompt,
            "session_id": self.session_id or "",
            "worktree": str(self.spec.worktree),
            "repo_root": str(self.state_dir.parent),
            "last_message_path": str(self.last_message_path),
            "agent_name": self.spec.name,
            "branch": self.spec.branch,
            "state_dir": str(self.state_dir),
            "resume": "true" if resume else "false",
        }
        rendered: list[str] = []
        for part in template:
            if part == "{global_extra_args}":
                rendered.extend(self.global_extra_args)
                continue
            if part == "{agent_extra_args}":
                rendered.extend(self.spec.extra_agent_args)
                continue
            rendered.append(part.format(**values))
        return rendered

    def spawn(self, prompt: str, *, resume: bool) -> None:
        if self.process is not None:
            raise RuntimeError(f"Agent {self.spec.name} already has a running process")

        if resume and self.resume_requires_session and not self.session_id:
            raise RuntimeError(
                f"Agent {self.spec.name} cannot resume without a recorded session id"
            )

        if resume and self.resume_command_template is not None:
            cmd = self._render_command_template(self.resume_command_template, prompt, resume=True)
        elif not resume and self.initial_command_template is not None:
            cmd = self._render_command_template(self.initial_command_template, prompt, resume=False)
        else:
            cmd = self._base_exec_args()
            if cli_backend_name(self.agent_cli) == "opencode":
                cmd.extend(["--dir", str(self.spec.worktree)])
                if resume:
                    cmd.extend(["--session", self.session_id or ""])
                cmd.extend(self.spec.extra_agent_args)
                cmd.append(prompt)
            else:
                cmd.extend(["-o", str(self.last_message_path)])
                if resume:
                    cmd.extend(["resume", self.session_id or "", prompt])
                else:
                    cmd.extend(["-C", str(self.spec.worktree), prompt])
                cmd.extend(self.spec.extra_agent_args)

        self.last_spawn_ts = now_ts()
        self.last_event_ts = self.last_spawn_ts
        self.pending_prompt = None
        self.last_status = "running"
        self.last_message_path.write_text("", encoding="utf-8")
        self.save_state()

        env = os.environ.copy()
        self.process = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            bufsize=1,
            env=env,
        )
        self.reader_thread = threading.Thread(target=self._reader, daemon=True)
        self.reader_thread.start()
        self.append_log(
            f"# {time.strftime('%Y-%m-%d %H:%M:%S')} "
            f"spawn resume={resume} cmd={shlex.join(cmd)}"
        )

    def start_initial(self) -> None:
        self.spawn(self.compose_initial_prompt(), resume=False)

    def start_resume(self, template: str) -> None:
        self.spawn(self.compose_resume_prompt(template), resume=True)

    def handle_event_line(self, line: str) -> None:
        self.raw_event_count += 1
        self.last_event_ts = now_ts()
        self.append_log(line)
        try:
            event = json.loads(line)
        except json.JSONDecodeError:
            self.save_state()
            return

        self.json_event_count += 1
        event_type = str(event.get("type", ""))
        session_id = event.get("sessionID")
        if isinstance(session_id, str) and session_id:
            self.session_id = session_id
        if event_type == "thread.started":
            thread_id = event.get("thread_id")
            if isinstance(thread_id, str) and thread_id:
                self.session_id = thread_id
        elif event_type == "turn.started":
            self.last_status = "turn.started"
        elif event_type == "turn.completed":
            self.last_status = "turn.completed"
        elif event_type == "step_start":
            self.last_status = "step_start"
        elif event_type == "step_finish":
            self.last_status = "step_finish"
        elif event_type == "error":
            message = event.get("message")
            if not isinstance(message, str):
                error = event.get("error")
                if isinstance(error, dict):
                    data = error.get("data")
                    if isinstance(data, dict):
                        message = data.get("message")
            self.last_status = f"error: {message or ''}"
        elif event_type == "text":
            part = event.get("part")
            if isinstance(part, dict):
                text = part.get("text")
                if isinstance(text, str) and text:
                    existing = read_text(self.last_message_path)
                    self.last_message_path.write_text(existing + text, encoding="utf-8")
        elif event_type == "item.completed":
            item = event.get("item")
            if isinstance(item, dict) and item.get("type") == "agent_message":
                text = item.get("text")
                if isinstance(text, str) and text.strip():
                    self.last_message_path.write_text(text, encoding="utf-8")
        self.save_state()

    def poll_output(self) -> None:
        while True:
            try:
                line = self.event_queue.get_nowait()
            except queue.Empty:
                break
            self.handle_event_line(line)

    def current_last_message(self) -> str:
        return read_text(self.last_message_path).strip()

    def resolve_status_path(self) -> Path | None:
        if not self.spec.status_file:
            return None
        return self.spec.worktree / self.spec.status_file

    def resolve_summary_path(self) -> Path | None:
        if not self.spec.status_file:
            return None
        status_path = self.resolve_status_path()
        if status_path is None:
            return None
        return status_path.with_name("summary.md")

    def should_stop_after_success(self) -> bool:
        last_message = self.current_last_message()
        if self.spec.done_marker and self.spec.done_marker in last_message:
            return True
        return self.round_index >= self.spec.max_rounds

    def maybe_mark_stalled(self, stall_seconds: int) -> bool:
        if self.process is None or self.done:
            return False
        age = now_ts() - self.last_event_ts
        if age < stall_seconds:
            return False
        self.stall_warnings += 1
        self.last_status = f"stalled>{stall_seconds}s"
        self.save_state()
        return True

    def interrupt_for_stall(self) -> None:
        if self.process is None:
            return
        self.append_log(
            f"# {time.strftime('%Y-%m-%d %H:%M:%S')} interrupt due to stall"
        )
        self.process.terminate()

    def on_process_exit(self) -> None:
        if self.process is None:
            return
        code = self.process.poll()
        if code is None:
            return

        if self.reader_thread is not None:
            self.reader_thread.join(timeout=1.0)
        self.poll_output()

        self.last_exit_code = code
        self.process = None
        self.reader_thread = None

        if code == 0:
            self.retry_count = 0
            self.round_index += 1
            self.proposed_done = bool(
                self.spec.done_marker and self.spec.done_marker in self.current_last_message()
            )
            if self.should_stop_after_success():
                self.done = False
                if self.require_judge_approval:
                    if self.proposed_done:
                        self.last_status = "proposed-done"
                    else:
                        self.last_status = "awaiting-judge"
                    self.pending_prompt = None
                else:
                    self.done = True
                    self.last_status = "done"
            else:
                self.pending_prompt = "nudge"
                self.last_status = "waiting-resume"
        else:
            self.proposed_done = False
            self.failures += 1
            self.retry_count += 1
            if self.retry_count > self.spec.max_retries:
                self.done = True
                self.last_status = f"failed rc={code}"
            else:
                self.pending_prompt = "recovery"
                self.last_status = f"retry rc={code}"
        self.save_state()

    def launch_pending_if_needed(self) -> None:
        if self.done or self.process is not None:
            return
        try:
            if self.pending_prompt == "nudge":
                self.start_resume(self.nudge_prompt)
            elif self.pending_prompt == "recovery":
                self.start_resume(self.recovery_prompt)
            elif self.pending_prompt == "stall":
                self.start_resume(self.stall_prompt)
            elif self.round_index == 0 and self.session_id is None:
                self.start_initial()
            elif (
                self.session_id is not None
                and not self.done
                and (
                    self.last_status == "waiting-resume"
                    or self.last_status.startswith("retry rc=")
                    or self.last_status == "judge:continue"
                    or self.last_status == "judge:retry"
                    or self.last_status == "judge:blocked"
                    or self.last_status == "judge-unavailable"
                )
            ):
                self.append_log(
                    f"# {time.strftime('%Y-%m-%d %H:%M:%S')} recovery: "
                    f"agent has session but no pending_prompt and no process; "
                    f"launching recovery resume"
                )
                self.start_resume(self.recovery_prompt)
        except Exception as exc:
            self.done = True
            self.last_status = f"failed launch: {type(exc).__name__}"
            self.append_log(
                f"# {time.strftime('%Y-%m-%d %H:%M:%S')} launch failed: "
                f"{type(exc).__name__}: {exc}"
            )
            self.save_state()

    def status_line(self) -> str:
        pid = self.process.pid if self.process else "-"
        last_age = format_age(now_ts() - self.last_event_ts)
        return (
            f"{self.spec.name:<18} pid={pid!s:<7} round={self.round_index:<2} "
            f"proposal={'yes' if self.proposed_done else 'no':<3} "
            f"retry={self.retry_count:<2} status={self.last_status:<22} "
            f"last={last_age:<8} session={self.session_id or '-'}"
        )


class Orchestrator:
    def __init__(self, config_path: Path) -> None:
        self.config_path = config_path.resolve()
        self.config_dir = self.config_path.parent
        self.config = load_json(self.config_path)
        self.repo_root = resolve_path(self.config_dir, self.config.get("repo_root")) or Path.cwd()
        self.repo_root = self.repo_root.resolve()
        self.agent_cli = str(self.config.get("agent_cli", self.config.get("codex_bin", "codex")))
        self.model = self.config.get("model")
        self.full_auto = bool(self.config.get("full_auto", True))
        self.json_output = bool(self.config.get("json_output", True))
        self.resume_requires_session = bool(self.config.get("resume_requires_session", True))
        initial_template = self.config.get("initial_command_template")
        resume_template = self.config.get("resume_command_template")
        judge_template = self.config.get("judge_command_template")
        self.initial_command_template = (
            list(initial_template) if isinstance(initial_template, list) else None
        )
        self.resume_command_template = (
            list(resume_template) if isinstance(resume_template, list) else None
        )
        self.judge_command_template = (
            list(judge_template) if isinstance(judge_template, list) else None
        )
        self.stall_seconds = int(self.config.get("stall_seconds", 900))
        self.status_interval = int(self.config.get("status_interval", 30))
        self.enable_judge = bool(self.config.get("enable_judge", False))
        self.require_judge_approval = bool(
            self.config.get("require_judge_approval", self.enable_judge)
        )
        self.judge_model = self.config.get("judge_model", self.model)
        state_dir = self.config.get("state_dir", ".orchestrator")
        self.state_dir = resolve_path(self.repo_root, state_dir) or (self.repo_root / ".orchestrator")
        ensure_dir(self.state_dir)
        self.common_prompt = str(self.config.get("common_prompt", "")).strip()
        self.nudge_prompt = str(
            self.config.get(
                "nudge_prompt",
                "Continue your assigned exploration in `{worktree}`. Before you stop, "
                "run at least one new experiment and record concrete pass/fail evidence in "
                "`{status_file}`. If the scope is finished, reply with `{done_marker} ...`."
                "\n\nLast message excerpt:\n{last_message}",
            )
        )
        self.recovery_prompt = str(
            self.config.get(
                "recovery_prompt",
                "The previous run for `{agent_name}` ended unexpectedly. Resume the same "
                "session, avoid repeating already-finished work, and continue from the latest "
                "stable point in `{worktree}`. Record progress in `{status_file}`. If you are "
                "fully done, reply with `{done_marker} ...`."
                "\n\nLast message excerpt:\n{last_message}",
            )
        )
        self.stall_prompt = str(
            self.config.get(
                "stall_prompt",
                "The last turn for `{agent_name}` appears stalled. Re-orient quickly: summarize "
                "what is already known, pick the next smallest experiment, and execute it now. "
                "Record concrete findings in `{status_file}`. If your assigned scope is complete, "
                "reply with `{done_marker} ...`."
                "\n\nLast message excerpt:\n{last_message}",
            )
        )
        self.global_extra_args = list(
            self.config.get("extra_agent_args", self.config.get("extra_codex_args", []))
        )
        self.judge_common_prompt = str(
            self.config.get(
                "judge_common_prompt",
                "You are a supervisor judge. Return a single JSON object prefixed with "
                f"`{DEFAULT_JUDGE_DONE_MARKER}` describing whether the worker has finished. "
                "Use decision in {done, continue, blocked, retry}.",
            )
        ).strip()
        self.agents = self._load_agents()

    def _load_agents(self) -> list[AgentRuntime]:
        agents_data = self.config.get("agents", [])
        if not isinstance(agents_data, list) or not agents_data:
            raise ValueError("config must contain a non-empty 'agents' list")

        runtimes: list[AgentRuntime] = []
        for idx, item in enumerate(agents_data):
            if not isinstance(item, dict):
                raise ValueError(f"agents[{idx}] must be an object, got {type(item).__name__}")
            agent_label = item.get("name", f"agents[{idx}]")
            for required_key in ("name", "branch", "worktree"):
                if required_key not in item:
                    raise ValueError(f"agent '{agent_label}' is missing required field '{required_key}'")
            prompt = item.get("prompt")
            prompt_file = item.get("prompt_file")
            if prompt is None and prompt_file is None:
                raise ValueError(
                    f"agent '{agent_label}' needs either 'prompt' or 'prompt_file'"
                )
            if prompt is None:
                prompt_path = resolve_path(self.config_dir, prompt_file)
                if prompt_path is None:
                    raise ValueError("prompt_file path could not be resolved")
                if not prompt_path.exists():
                    raise FileNotFoundError(
                        f"prompt_file does not exist for agent '{agent_label}': "
                        f"{prompt_path}"
                    )
                prompt = read_text(prompt_path)

            worktree = resolve_path(self.repo_root, item["worktree"])
            if worktree is None:
                raise ValueError("worktree path could not be resolved")

            spec = AgentSpec(
                name=str(item["name"]),
                branch=str(item["branch"]),
                worktree=worktree,
                base_branch=str(item.get("base_branch", self.config.get("base_branch", "main"))),
                prompt=str(prompt),
                status_file=item.get("status_file"),
                max_rounds=int(item.get("max_rounds", self.config.get("max_rounds", 4))),
                max_retries=int(item.get("max_retries", self.config.get("max_retries", 2))),
                extra_agent_args=list(
                    item.get("extra_agent_args", item.get("extra_codex_args", []))
                ),
                done_marker=str(item.get("done_marker", DEFAULT_DONE_MARKER)),
                interrupt_stalled=bool(
                    item.get("interrupt_stalled", self.config.get("interrupt_stalled", False))
                ),
                judge_prompt=item.get("judge_prompt"),
            )

            ensure_worktree(self.repo_root, spec.worktree, spec.branch, spec.base_branch)

            runtimes.append(
                AgentRuntime(
                    spec=spec,
                    state_dir=self.state_dir,
                    agent_cli=self.agent_cli,
                    model=self.model,
                    full_auto=self.full_auto,
                    json_output=self.json_output,
                    common_prompt=self.common_prompt,
                    nudge_prompt=self.nudge_prompt,
                    recovery_prompt=self.recovery_prompt,
                    stall_prompt=self.stall_prompt,
                    global_extra_args=self.global_extra_args,
                    require_judge_approval=self.require_judge_approval,
                    initial_command_template=self.initial_command_template,
                    resume_command_template=self.resume_command_template,
                    resume_requires_session=self.resume_requires_session,
                )
            )
        return runtimes

    def print_status(self) -> None:
        print("=" * 100)
        print(time.strftime("%Y-%m-%d %H:%M:%S"), "agent status")
        for agent in self.agents:
            print(agent.status_line())
        sys.stdout.flush()

    def terminate_all(self) -> None:
        for agent in self.agents:
            if agent.process is not None and agent.process.poll() is None:
                agent.append_log(
                    f"# {time.strftime('%Y-%m-%d %H:%M:%S')} terminate_all signal"
                )
                agent.process.terminate()

    def run_judge(self, agent: AgentRuntime) -> dict[str, Any] | None:
        if not self.enable_judge:
            return None

        status_path = agent.resolve_status_path()
        summary_path = agent.resolve_summary_path()
        status_text = ""
        summary_text = ""
        if status_path and status_path.exists():
            status_text = clip_text(read_text(status_path), 5000)
        if summary_path and summary_path.exists():
            summary_text = clip_text(read_text(summary_path), 7000)

        judge_prompt = agent.spec.judge_prompt or (
            "Decide whether the worker has completed its assigned scope.\n"
            "Inputs available below:\n"
            f"- worker name: {agent.spec.name}\n"
            f"- worktree: {agent.spec.worktree}\n"
            f"- status file hint: {agent.spec.status_file or 'none'}\n"
            f"- last message:\n{clip_text(agent.current_last_message(), 4000)}\n\n"
            f"- status.json excerpt:\n{status_text or '[missing]'}\n\n"
            f"- summary.md excerpt:\n{summary_text or '[missing]'}\n\n"
            "Return exactly one line beginning with "
            f"`{DEFAULT_JUDGE_DONE_MARKER}` followed by a JSON object like "
            '{"decision":"continue","reason":"...","next_instruction":"..."}'
        )
        prompt = f"{self.judge_common_prompt}\n\n{judge_prompt}"
        out_path = self.state_dir / f"{agent.spec.name}.judge.last.txt"
        if self.judge_command_template is not None:
            values = {
                "agent_cli": self.agent_cli,
                "model": str(self.judge_model or ""),
                "prompt": prompt,
                "repo_root": str(self.repo_root),
                "worktree": str(agent.spec.worktree),
                "last_message_path": str(out_path),
                "agent_name": agent.spec.name,
                "branch": agent.spec.branch,
                "state_dir": str(self.state_dir),
            }
            cmd = []
            for part in self.judge_command_template:
                if part == "{global_extra_args}":
                    cmd.extend(self.global_extra_args)
                elif part == "{agent_extra_args}":
                    cmd.extend(agent.spec.extra_agent_args)
                else:
                    cmd.append(part.format(**values))
        else:
            if cli_backend_name(self.agent_cli) == "opencode":
                cmd = [self.agent_cli, "run"]
                if self.full_auto:
                    cmd.append("--dangerously-skip-permissions")
                cmd.extend(["--format", "json"])
                if self.judge_model:
                    cmd.extend(["--model", str(self.judge_model)])
                cmd.extend(self.global_extra_args)
                cmd.extend(["--dir", str(self.repo_root), prompt])
            else:
                cmd = [self.agent_cli, "exec"]
                if self.full_auto:
                    cmd.append("--full-auto")
                cmd.extend(["--json"])
                if self.judge_model:
                    cmd.extend(["-m", str(self.judge_model)])
                cmd.extend(self.global_extra_args)
                cmd.extend(["-C", str(self.repo_root), "-o", str(out_path), prompt])

        proc = subprocess.run(cmd, text=True, capture_output=True)
        agent.judge_runs += 1
        agent.save_state()
        if proc.returncode != 0:
            agent.append_log(
                f"# {time.strftime('%Y-%m-%d %H:%M:%S')} judge failed rc={proc.returncode}"
            )
            return None

        payload = out_path.read_text(encoding="utf-8") if out_path.exists() else ""
        if cli_backend_name(self.agent_cli) == "opencode":
            payload = extract_opencode_text(proc.stdout)
            out_path.write_text(payload, encoding="utf-8")
        elif not payload:
            payload = proc.stdout
        marker_index = payload.find(DEFAULT_JUDGE_DONE_MARKER)
        if marker_index == -1:
            return None
        raw = payload[marker_index + len(DEFAULT_JUDGE_DONE_MARKER) :].strip()
        try:
            return json.loads(raw)
        except json.JSONDecodeError:
            return None

    def run(self) -> int:
        last_status_print = 0.0
        try:
            for agent in self.agents:
                if not agent.done and agent.process is None:
                    agent.launch_pending_if_needed()

            while True:
                active_or_pending = False
                for agent in self.agents:
                    agent.poll_output()
                    if agent.process is not None:
                        active_or_pending = True
                        if agent.maybe_mark_stalled(self.stall_seconds):
                            print(
                                f"[warn] {agent.spec.name} appears stalled for "
                                f"{self.stall_seconds}s"
                            )
                            if agent.spec.interrupt_stalled and agent.session_id:
                                agent.interrupt_for_stall()
                                agent.pending_prompt = "stall"
                    agent.on_process_exit()
                    if agent.process is None and not agent.done and self.enable_judge:
                        judge = self.run_judge(agent)
                        if isinstance(judge, dict):
                            decision = str(judge.get("decision", "")).lower()
                            next_instruction = str(judge.get("next_instruction", "")).strip()
                            if decision == "done":
                                agent.done = True
                                agent.last_status = "done(judge)"
                                agent.pending_prompt = None
                                agent.save_state()
                            elif decision == "continue":
                                agent.done = False
                                agent.proposed_done = False
                                if next_instruction:
                                    agent.pending_prompt = "nudge"
                                    agent.last_message_path.write_text(
                                        next_instruction, encoding="utf-8"
                                    )
                                else:
                                    agent.pending_prompt = "nudge"
                                agent.last_status = "judge:continue"
                                agent.save_state()
                            elif decision == "retry":
                                agent.done = False
                                agent.proposed_done = False
                                if next_instruction:
                                    agent.pending_prompt = "recovery"
                                    agent.last_message_path.write_text(
                                        next_instruction, encoding="utf-8"
                                    )
                                else:
                                    agent.pending_prompt = "recovery"
                                agent.last_status = "judge:retry"
                                agent.save_state()
                            elif decision == "blocked":
                                agent.done = False
                                if next_instruction:
                                    agent.pending_prompt = "stall"
                                    agent.last_message_path.write_text(
                                        next_instruction, encoding="utf-8"
                                    )
                                else:
                                    agent.pending_prompt = "stall"
                                agent.last_status = "judge:blocked"
                                agent.save_state()
                        elif agent.require_judge_approval and agent.last_status in {
                            "proposed-done",
                            "awaiting-judge",
                        }:
                            agent.pending_prompt = "stall"
                            agent.last_status = "judge-unavailable"
                            agent.save_state()
                    if not agent.done:
                        active_or_pending = True
                        if agent.process is None:
                            agent.launch_pending_if_needed()

                if now_ts() - last_status_print >= self.status_interval:
                    self.print_status()
                    last_status_print = now_ts()

                if not active_or_pending:
                    break
                time.sleep(1.0)
        except KeyboardInterrupt:
            print("\nInterrupted. Terminating child agent processes...", file=sys.stderr)
            self.terminate_all()
            return 130

        self.print_status()
        failed = [agent for agent in self.agents if agent.last_status.startswith("failed")]
        return 1 if failed else 0


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Launch multiple CLI-driven agent workers against isolated git worktrees."
    )
    parser.add_argument(
        "--config",
        required=True,
        help="Path to the orchestrator JSON config.",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    orchestrator = Orchestrator(Path(args.config))
    return orchestrator.run()


if __name__ == "__main__":
    raise SystemExit(main())
