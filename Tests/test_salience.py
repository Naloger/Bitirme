import os
import sys
import unittest
from unittest.mock import MagicMock, patch

# Ensure project root is in sys.path
_here = os.path.dirname(os.path.abspath(__file__))
_root = os.path.abspath(os.path.join(_here, "../services", ".."))
if _root not in sys.path:
    sys.path.insert(0, _root)

from services.Agentic.MainAgents.SalienceMode.SalienceGraphBuilder import (
    build_salience_graph,
)
from services.Agentic.MainAgents.SalienceMode.SalienceModels import SalienceState
from services.Agentic.MainAgents.SalienceMode.SalienceNodes import (
    run_default_subgraph,
    run_executive_subgraph,
    salience_router_node,
)


class TestSalienceMode(unittest.TestCase):
    def setUp(self):
        self.state = SalienceState(user_input="Test input")

    @patch("services.Agentic.MainAgents.SalienceMode.SalienceNodes.call_llm")
    def test_router_decides_executive_control_mode(self, mock_call_llm):
        """Test that router selects ExecutiveControlMode based on LLM JSON response."""
        mock_call_llm.return_value = (
            '{"target": "ExecutiveControlMode", "explanation": "Requires search"}'
        )

        res = salience_router_node(self.state)
        self.assertEqual(res.target_subgraph, "ExecutiveControlMode")
        self.assertEqual(res.explanation, "Requires search")

    @patch("services.Agentic.MainAgents.SalienceMode.SalienceNodes.call_llm")
    def test_router_decides_default_mode(self, mock_call_llm):
        """Test that router selects DefaultMode based on LLM JSON response."""
        mock_call_llm.return_value = (
            '{"target": "DefaultMode", "explanation": "Simple mapping"}'
        )

        res = salience_router_node(self.state)
        self.assertEqual(res.target_subgraph, "DefaultMode")
        self.assertEqual(res.explanation, "Simple mapping")

    @patch("services.Agentic.MainAgents.SalienceMode.SalienceNodes.call_llm")
    def test_router_parsing_fallback(self, mock_call_llm):
        """Test router fallback logic when LLM output is not valid JSON."""
        mock_call_llm.return_value = "invalid response text"

        res = salience_router_node(self.state)
        self.assertEqual(res.target_subgraph, "ExecutiveControlMode")
        self.assertTrue(res.explanation.startswith("Fallback"))

    @patch("services.Agentic.MainAgents.ExecutiveControlMode.ExecutiveControlExecutor.default_initial_state")
    @patch("services.Agentic.MainAgents.ExecutiveControlMode.ExecutiveControlGraphBuilder.build_ecn_graph")
    def test_run_executive_subgraph(self, mock_build, mock_init):
        """Test that executive subgraph execution maps the result state properly."""
        mock_graph = MagicMock()
        mock_res = MagicMock()
        mock_res.reasoning = "ECN Reasoning Output"
        mock_res.model_dump.return_value = {"reasoning": "ECN Reasoning Output"}
        mock_graph.invoke.return_value = mock_res
        mock_build.return_value = mock_graph

        res = run_executive_subgraph(self.state)
        self.assertEqual(res.result, "ECN Reasoning Output")
        self.assertEqual(res.ecn_state, {"reasoning": "ECN Reasoning Output"})

    @patch("services.Agentic.MainAgents.SalienceMode.SalienceNodes.build_loop_subgraph")
    def test_run_default_subgraph(self, mock_build):
        """Test that default subgraph execution maps the loop state properly."""
        mock_graph = MagicMock()
        mock_res = MagicMock()
        mock_res.iteration = 4
        mock_res.decision = {"actions": [{"type": "log"}]}
        mock_res.model_dump.return_value = {"iteration": 4, "decision": {"actions": [{"type": "log"}]}}
        mock_graph.invoke.return_value = mock_res
        mock_build.return_value = mock_graph

        res = run_default_subgraph(self.state)
        self.assertIn("Completed Loop Subgraph in 4 iterations", res.result)
        self.assertEqual(res.loop_state, {"iteration": 4, "decision": {"actions": [{"type": "log"}]}})

    @patch("services.Agentic.MainAgents.SalienceMode.SalienceNodes.call_llm")
    @patch("services.Agentic.MainAgents.SalienceMode.SalienceGraphBuilder.run_executive_subgraph")
    @patch("services.Agentic.MainAgents.SalienceMode.SalienceGraphBuilder.run_default_subgraph")
    def test_full_salience_graph_routing_executive(self, mock_run_default, mock_run_exec, mock_call_llm):
        """Test full graph execution routing to ExecutiveControlMode."""
        mock_call_llm.return_value = '{"target": "ExecutiveControlMode", "explanation": "Requires search"}'
        mock_run_exec.return_value = self.state.model_copy(update={"result": "ECN Mocked output", "target_subgraph": "ExecutiveControlMode"})

        graph = build_salience_graph()
        res = graph.invoke(self.state)

        self.assertEqual(res["result"], "ECN Mocked output")
        mock_run_exec.assert_called_once()
        mock_run_default.assert_not_called()



if __name__ == "__main__":
    unittest.main(verbosity=2)
