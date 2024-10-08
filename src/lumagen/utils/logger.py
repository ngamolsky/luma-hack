import asyncio
import logging
from contextlib import asynccontextmanager
from contextvars import ContextVar
from time import time
from typing import Dict, List, Optional

from rich.columns import Columns
from rich.console import Console
from rich.live import Live
from rich.panel import Panel
from rich.progress import BarColumn, Progress, TaskID, TextColumn
from rich.text import Text
from rich.tree import Tree


class TaskNode:
    def __init__(
        self,
        description: str,
        parent: Optional["TaskNode"] = None,
        log_level: int = logging.INFO,
    ):
        self.description = description
        self.parent = parent
        self.children: List["TaskNode"] = []
        self.logs: List[Text] = []
        self.start_time = time()
        self.end_time: Optional[float] = None
        self.is_complete = False
        self.progress: Optional[Progress] = None
        self.progress_total: Optional[int] = None
        self.progress_completed: int = 0
        self.log_level = log_level

    def add_child(self, child: "TaskNode"):
        self.children.append(child)

    def add_log(self, log: Text):
        self.logs.append(log)

    def create_progress(self):
        self.progress = Progress(
            TextColumn("[progress.percentage]{task.percentage:>3.0f}%"),
            BarColumn(complete_style="magenta", finished_style="bold magenta"),
            TextColumn("{task.completed}/{task.total}"),
            expand=True,
        )
        self.progress_task_id = self.progress.add_task(
            self.description, total=self.progress_total
        )

    def complete(self):
        self.end_time = time()
        self.is_complete = True

    def update_progress(self, completed: int, total: Optional[int] = None):
        self.progress_completed = completed
        if total is not None:
            self.progress_total = total


class WorkflowLogger:
    _instance = None
    _current_task: ContextVar[Optional[TaskNode]] = ContextVar(
        "current_task", default=None
    )

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(WorkflowLogger, cls).__new__(cls)
            cls._instance.initialize()
        return cls._instance

    def initialize(self):
        self.console = Console()
        self.root_task = TaskNode("[WORKFLOW]")
        self.live = Live(
            console=self.console,
            refresh_per_second=4,
        )
        self.update_task = None
        self.progress = Progress(
            TextColumn("[progress.percentage]{task.percentage:>3.0f}%"),
            BarColumn(complete_style="magenta", finished_style="bold magenta"),
            TextColumn("{task.completed}/{task.total}"),
            console=self.console,
            expand=True,
        )
        self.progress_tasks = {}
        del self.progress
        self.task_log_levels: Dict[str, int] = {}
        self.default_log_level = logging.INFO

    def start(self):
        self.live.start()
        self.update_task = asyncio.create_task(self._update_tree())

    def stop(self):
        if self.update_task:
            self.update_task.cancel()
        self.root_task.complete()
        # Force a final update before stopping
        self.live.update(self._create_panel())
        self.live.stop()

    async def _update_tree(self):
        while True:
            self.live.update(self._create_panel())
            await asyncio.sleep(0.25)

    def _create_panel(self):
        tree = self._build_tree(self.root_task)
        return Panel(
            tree,
            title="[bold magenta]LumaGen[/bold magenta]",
            border_style="cyan",
            padding=(1, 1),
            expand=True,
        )

    def _build_tree(self, task_node: TaskNode) -> Tree:
        elapsed = (task_node.end_time or time()) - task_node.start_time
        label = self._format_task_label(
            task_node.description, elapsed, task_node.is_complete
        )

        if task_node.progress is not None:
            label = Columns([label, task_node.progress])

        tree = Tree(label)

        for log in task_node.logs:
            tree.add(log)

        for child in task_node.children:
            tree.add(self._build_tree(child))

        return tree

    def _format_task_label(
        self, description: str, elapsed_time: float, is_complete: bool
    ) -> Text:
        checkmark = "✓ " if is_complete else ""
        return Text.assemble(
            (description, "bold cyan"),
            " ",
            (checkmark, "bold green"),
            (f"({elapsed_time:.2f}s)", "magenta"),
        )

    def _format_log(self, message: str, level: int) -> Text:
        color = {
            logging.DEBUG: "white dim",
            logging.INFO: "white",
            logging.WARNING: "yellow",
            logging.ERROR: "bold red",
            logging.CRITICAL: "bold red on white",
        }[level]
        return Text.assemble(
            (f"{logging.getLevelName(level)}: ", color), (message, color)
        )

    def set_current_task_log_level(self, log_level: int):
        current_task = self._current_task.get()
        if current_task:
            current_task.log_level = log_level

    def set_task_log_level(self, task_name: str, log_level: int):
        self.task_log_levels[task_name] = log_level

    def set_default_log_level(self, log_level: int):
        self.default_log_level = log_level

    @asynccontextmanager
    async def task(self, description: str):
        parent_task = self._current_task.get()
        log_level = self.task_log_levels.get(description, self.default_log_level)
        new_task = TaskNode(description, parent_task, log_level)

        if parent_task:
            parent_task.add_child(new_task)
        else:
            self.root_task.add_child(new_task)

        token = self._current_task.set(new_task)
        try:
            yield
        finally:
            new_task.complete()
            self._current_task.reset(token)
            # Force an update after task completion
            self.live.update(self._create_panel())

    def log(self, message: str, level: int = logging.INFO):
        current_task = self._current_task.get()
        task_log_level = (
            current_task.log_level if current_task else self.default_log_level
        )

        if level >= task_log_level:
            log_message = self._format_log(message, level)

            if current_task:
                current_task.add_log(log_message)
            else:
                self.root_task.add_log(log_message)

    def error(self, message: str):
        self.log(message, logging.ERROR)

    def warning(self, message: str):
        self.log(message, logging.WARNING)

    def info(self, message: str):
        self.log(message, logging.INFO)

    def debug(self, message: str):
        self.log(message, logging.DEBUG)

    def print_tree(self):
        self.console.print(self._create_panel())

    def start_progress(self, total: int) -> TaskID:
        current_task = self._current_task.get()
        if current_task:
            current_task.progress_total = total
            current_task.create_progress()

            return current_task.progress_task_id
        else:
            raise ValueError("No active task to start progress on")

    def update_progress(self, increment: int = 1):
        current_task = self._current_task.get()
        if current_task and current_task.progress is not None:
            current_task.progress.update(
                current_task.progress_task_id, advance=increment
            )
            current_task.progress_completed += increment
            if current_task.progress_total is not None:
                current_task.progress_completed = min(
                    current_task.progress_completed, current_task.progress_total
                )
            current_task.update_progress(current_task.progress_completed)
            if current_task.progress_completed == current_task.progress_total:
                current_task.progress.update(
                    current_task.progress_task_id,
                    completed=current_task.progress_total,
                )
        else:
            raise ValueError("No active task with progress to update")
