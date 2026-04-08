import json
from pathlib import Path

import networkx as nx


class NodeLinkFormat:
    """Lossless JSON codec using NetworkX's node-link format."""

    @property
    def format_name(self) -> str:
        return "node_link_json"

    def render(self, graph: nx.MultiDiGraph) -> str:
        data = nx.node_link_data(graph)
        # Inject a "labels" list expected by CMiner's NetworksLoading JSON reader.
        # CMiner looks for node["labels"] (a list), not "type" or "label".
        # TODO: do not seem too elegant
        for node in data.get("nodes", []):
            if "labels" not in node:
                ntype = node.get("type") or node.get("label") or ""
                node["labels"] = [ntype] if ntype else []
        return json.dumps(data, indent=2, ensure_ascii=False)

    def render_corpus(self, graphs: dict[str, nx.MultiDiGraph], output_dir: Path) -> None:
        """One .json file per graph."""
        output_dir.mkdir(parents=True, exist_ok=True)
        for name, graph in graphs.items():
            path = output_dir / f"{name}.json"
            path.write_text(self.render(graph), encoding="utf-8")

    def parse(self, text: str) -> list[nx.MultiDiGraph]:
        data = json.loads(text)
        graph = nx.node_link_graph(data, directed=True, multigraph=True)
        return [graph]