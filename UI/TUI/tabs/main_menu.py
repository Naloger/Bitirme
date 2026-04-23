"""Main LLM Menu interface."""
from textual.app import ComposeResult
from textual.containers import Container
from textual.widgets import ContentSwitcher, Static, Tabs, Tab

from UI.TUI.tabs.chat_tab import ChatTab
from UI.TUI.tabs.graph_visualizer import GraphVisualizer
from UI.TUI.tabs.memory_visualizer import MemoryVisualizer
from UI.TUI.tabs.configure import Configure



class MainMenuContainer(Container):
    """Container for LLM Assistant content with tabbed interface."""

    TAB_TO_PANEL = {
        "tab_chat": "panel_chat",
        "tab_graph": "panel_graph",
        "tab_memory": "panel_memory",
        "tab_config": "panel_config",
    }

    CSS = """
    LLMAssistantContainer {
        width: 100%;
        height: 1fr;
        layout: vertical;
    }
    
    LLMAssistantContainer #llm-header {
        width: 100%;
        height: 3;
        background: $boost;
        border-bottom: solid $accent;
        content-align: center middle;
    }
    
    LLMAssistantContainer #llm-header Static {
        width: 100%;
        text-align: center;
    }
    
    LLMAssistantContainer #llm-tabs {
        width: 100%;
        height: auto;
        dock: top;
    }
    
    LLMAssistantContainer #llm-main {
        width: 100%;
        height: 1fr;
        background: $surface;
    }
    
    LLMAssistantContainer .tab-panel {
        width: 100%;
        height: 100%;
        layout: vertical;
    }
    
    """


    def compose(self) -> ComposeResult:
        """Create child widgets for the LLM Assistant container."""
        # Header
        with Container(id="llm-header"):
            yield Static("[bold cyan]LLM Assistant[/bold cyan]")

        # Tab navigation
        yield Tabs(
            Tab("Chat", id="tab_chat"),
            Tab("Graph", id="tab_graph"),
            Tab("Memory", id="tab_memory"),
            Tab("Configure", id="tab_config"),
            id="llm-tabs",
        )

        # Main container with tabs
        with ContentSwitcher(initial="panel_chat", id="llm-main"):
            # Chat Tab
            with Container(id="panel_chat", classes="tab-panel"):
                yield ChatTab()

            # Graph State Visualizer Tab
            with Container(id="panel_graph", classes="tab-panel"):
                yield GraphVisualizer()

            # Memory Visualizer Tab
            with Container(id="panel_memory", classes="tab-panel"):
                yield MemoryVisualizer()

            # Configure Tab
            with Container(id="panel_config", classes="tab-panel"):
                yield Configure()


    def on_tabs_tab_activated(self, event: Tabs.TabActivated) -> None:
        """Switch to the selected tab panel."""
        tab_id = event.tab.id
        if tab_id is not None:
            panel_id = self.TAB_TO_PANEL.get(tab_id)
            if panel_id:
                self.query_one("#llm-main", ContentSwitcher).current = panel_id

    def on_mount(self) -> None:
        """Ensure default tab and panel on app start."""
        self.query_one("#llm-tabs", Tabs).active = "tab_chat"
        self.query_one("#llm-main", ContentSwitcher).current = "panel_chat"



class MainMenu:
    """LLM Menu interface manager."""

    @staticmethod
    def compose() -> ComposeResult:
        """Create child widgets for the LLM menu."""
        yield MainMenuContainer()



