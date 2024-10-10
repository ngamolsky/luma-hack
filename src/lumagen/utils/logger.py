import logging
import queue
import threading
from contextlib import asynccontextmanager
from contextvars import ContextVar
from queue import Queue
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
        self.error: Optional[Exception] = None
        self.progress: Optional[Progress] = None
        self.progress_total: Optional[int] = None
        self.progress_completed: int = 0
        self.log_level = log_level
        self.retry_count: int = 0

    def add_child(self, child: "TaskNode"):
        self.children.append(child)

    def add_log(self, log: Text):
        self.logs.append(log)

    def create_progress(self, stage: Optional[str] = None):
        progress_columns = [
            TextColumn("[progress.percentage]{task.percentage:>3.0f}%"),
            BarColumn(complete_style="magenta", finished_style="bold magenta"),
        ]

        if stage:
            progress_columns.append(TextColumn("[{task.description}]"))
        else:
            progress_columns.append(TextColumn("{task.completed}/{task.total}"))

        self.progress = Progress(*progress_columns, expand=True)
        self.progress_task_id = self.progress.add_task(
            stage or self.description, total=self.progress_total
        )

    def complete(self):
        self.end_time = time()

        if not self.error:
            if (
                self.progress
                and self.progress_total is not None
                and self.progress_completed != self.progress_total
            ):
                # Don't set is_complete if progress is not finished
                pass
            else:
                self.is_complete = True
            self.retry_count = 0

    def update_progress(
        self, completed: int, total: Optional[int] = None, stage: Optional[str] = None
    ):
        self.progress_completed = completed
        if total is not None:
            self.progress_total = total
        if stage is not None:
            if self.progress:
                self.progress.update(self.progress_task_id, description=stage)

    def increment_retry_count(self):
        self.retry_count += 1


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
        self.update_queue = Queue()
        self.update_thread = None
        self.task_log_levels: Dict[str, int] = {}
        self.default_log_level = logging.INFO
        self._stop_event = threading.Event()

    def start(self):
        self.live.start()
        self.update_thread = threading.Thread(target=self._update_display)
        self.update_thread.start()

    def stop(self):
        self._stop_event.set()
        if self.update_thread:
            self.update_thread.join()
        self.root_task.complete()
        # Force a final update before stopping
        self.live.update(self._create_panel())
        self.live.stop()

    def _update_display(self):
        while not self._stop_event.is_set():
            try:
                # Wait for up to 0.1 seconds for a new update
                update_func = self.update_queue.get(timeout=0.1)
                update_func()
                self.live.update(self._create_panel())
            except queue.Empty:
                # If no update received, just refresh the display
                self.live.update(self._create_panel())

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
            task_node.description,
            elapsed,
            task_node.is_complete,
            task_node.error,
            task_node.retry_count,
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
        self,
        description: str,
        elapsed_time: float,
        is_complete: bool,
        error: Optional[Exception],
        retry_count: int,
    ) -> Text:
        checkmark = "✓ " if is_complete else "✗ " if error else ""
        retry_info = f" [Retry: {retry_count}]" if retry_count > 0 else ""
        return Text.assemble(
            (description, "bold cyan"),
            " ",
            (checkmark, "bold green " if is_complete else "bold red " if error else ""),
            (f"({elapsed_time:.2f}s)", "magenta"),
            (retry_info, "yellow dim"),
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
        except Exception as e:
            new_task.error = e
            raise e
        finally:
            # Process any remaining logs in the queue
            self._process_remaining_logs()

            new_task.complete()
            self._current_task.reset(token)
            # Queue an update after task completion
            self.update_queue.put(lambda: None)

    def _process_remaining_logs(self):
        while not self.update_queue.empty():
            update_func = self.update_queue.get_nowait()
            update_func()
        self.live.update(self._create_panel())

    def log(self, message: str, level: int = logging.INFO):
        current_task = self._current_task.get()
        task_log_level = (
            current_task.log_level if current_task else self.default_log_level
        )

        if level >= task_log_level:
            log_message = self._format_log(message, level)

            def _add_log():
                if current_task:
                    current_task.add_log(log_message)
                else:
                    self.root_task.add_log(log_message)

            self.update_queue.put(_add_log)

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

    def start_progress(self, total: int, stage: Optional[str] = None) -> TaskID:
        current_task = self._current_task.get()
        if current_task:
            current_task.progress_total = total
            current_task.create_progress(stage)

            return current_task.progress_task_id
        else:
            raise ValueError("No active task to start progress on")

    def update_progress(self, increment: int = 1, stage: Optional[str] = None):
        current_task = self._current_task.get()
        if current_task and current_task.progress is not None:

            def _update_progress():
                if current_task.progress:
                    current_task.progress.update(
                        current_task.progress_task_id, advance=increment
                    )
                current_task.progress_completed += increment
                if current_task.progress_total is not None:
                    current_task.progress_completed = min(
                        current_task.progress_completed, current_task.progress_total
                    )
                current_task.update_progress(
                    current_task.progress_completed, stage=stage
                )
                if (
                    current_task.progress
                    and current_task.progress_completed == current_task.progress_total
                ):
                    current_task.progress.update(
                        current_task.progress_task_id,
                        completed=current_task.progress_total,
                    )
                current_task.retry_count = 0

            self.update_queue.put(_update_progress)
        else:
            raise ValueError("No active task with progress to update")

    def increment_retry_count(self):
        current_task = self._current_task.get()
        if current_task:
            current_task.increment_retry_count()
            self.update_queue.put(lambda: None)  # Trigger an update
        else:
            raise ValueError("No active task to increment retry count")
