import asyncio
from contextlib import asynccontextmanager
from enum import Enum
from time import time
from typing import Any, Dict, Optional

from rich.console import Console
from rich.live import Live
from rich.panel import Panel
from rich.text import Text
from rich.tree import Tree


class LogLevel(Enum):
    INFO = "INFO"
    WARNING = "WARNING"
    ERROR = "ERROR"


class WorkflowLogger:
    def __init__(self):
        self.console = Console()
        self.tree = Tree("[bold blue]Workflow[/bold blue]")
        self.tasks: Dict[str, Any] = {}
        self.live = Live(
            console=self.console,
            refresh_per_second=4,
        )
        self.update_task = None
        self.start_time = None

    def start(self):
        self.start_time = time()
        self.live.start()
        self.update_task = asyncio.create_task(self._update_tree())

    def stop(self):
        if self.update_task:
            self.update_task.cancel()
        self.live.stop()
        if self.start_time is not None:
            total_elapsed = time() - self.start_time
            self.tree.label = f"[bold blue]Workflow[/bold blue] [cyan](Total: {total_elapsed:.2f}s)[/cyan]"
        else:
            self.tree.label = "[bold blue]Workflow[/bold blue]"

    async def _update_tree(self):
        while True:
            self._update_elapsed_times()
            self.live.update(self._create_panel())
            await asyncio.sleep(0.25)

    def _create_panel(self):
        return Panel(
            self.tree,
            title="[bold magenta]LumaGen[/bold magenta]",
            border_style="cyan",
            padding=(1, 1),
            expand=True,
        )

    def _update_elapsed_times(self):
        current_time = time()
        for task_info in self.tasks.values():
            if not task_info.get("completed", False):
                elapsed_time = current_time - task_info["start_time"]
                task_info["node"].label = self._format_task_label(
                    task_info["description"], elapsed_time
                )
        if self.start_time is not None:
            total_elapsed = current_time - self.start_time
            self.tree.label = f"[bold cyan][WORKFLOW][/bold cyan] [cyan](Total: {total_elapsed:.2f}s)[/cyan]"
        else:
            self.tree.label = "[bold cyan][WORKFLOW][/bold cyan]"

    def _format_task_label(self, description: str, elapsed_time: float) -> Text:
        return Text.assemble(
            (description, "bold cyan"),
            " ",
            (f"({elapsed_time:.2f}s)", "magenta"),
        )

    def log(
        self, message: str, level: LogLevel = LogLevel.INFO, task: Optional[str] = None
    ):
        color = {
            LogLevel.INFO: "white",
            LogLevel.WARNING: "yellow",
            LogLevel.ERROR: "red",
        }[level]
        log_message = Text.assemble(
            (f"{level.value}: ", f"bold {color}"), (message, color)
        )

        if task and task in self.tasks:
            self.tasks[task]["node"].add(log_message)
        else:
            self.tree.add(log_message)

        self.live.update(self._create_panel())

    @asynccontextmanager
    async def task(self, description: str, parent: Optional[str] = None):
        parent_node = self.tasks[parent]["node"] if parent else self.tree
        task_node = parent_node.add(self._format_task_label(description, 0))
        start_time = time()

        self.tasks[description] = {
            "node": task_node,
            "start_time": start_time,
            "description": description,
            "completed": False,
        }

        try:
            yield
        finally:
            elapsed_time = time() - start_time
            self.tasks[description]["completed"] = True
            task_node.label = Text.assemble(
                (description, "bold cyan"),
                " ",
                ("✓", "bold green"),
                f" ({elapsed_time:.2f}s)",
            )
            self.live.update(self._create_panel())

    def print_tree(self):
        self.console.print(self._create_panel())
