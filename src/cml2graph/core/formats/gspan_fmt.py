from collections.abc import Iterable
from dataclasses import dataclass, field
from pathlib import Path

import networkx as nx


@dataclass
class PatternResult:
    """A mined pattern: graph skeleton plus mining metrics."""

    graph: nx.MultiDiGraph
    support: float | None = None
    frequency: float | None = None
    info: str = ""


class GSpanFormat:
    """
    Bidirectional gSpan/graph_data codec.
    satisfies both Renderer and FormatCodec Protocol.
    It can handle the exapnded format tha CMiner produces.

    Works on any nx.MultiDiGraph whose nodes and edges carry at least
    a type field (the standard GraphNode / GraphEdge contract).

    gSpan text format:
        t # <index> [model_id]
        v <idx> <type>
        e <src_idx> <tgt_idx> <type>


    - Original node IDs are lost in gSpan (replaced by sequential ints).
    - Node names / labels beyond the type are not stored.
    - A render then parse cycle preserves graph "structure" and "type annotations" perfectly.
    """
    @property
    def format_name(self) -> str:
        return "gspan"

    def render(self, graph: nx.MultiDiGraph) -> str:
        return self._render_one(graph, index=0)

    def render_corpus(self, graphs: Iterable[nx.MultiDiGraph]) -> str:
        blocks: list[str] = []
        for idx, g in enumerate(graphs):
            blocks.append(self._render_one(g, index=idx))
        return "\n".join(blocks)

    def parse(self, text: str) -> list[nx.MultiDiGraph]:
        """Parse plain gSpan text. Ignores extended fields."""
        results = self.parse_patterns(text)
        return [r.graph for r in results]

    def parse_file(self, path: str | Path) -> list[nx.MultiDiGraph]:
        return self.parse(Path(path).read_text(encoding="utf-8"))

    def parse_patterns(self, text: str) -> list[PatternResult]:
        """
        Parse gSpan text that may include extended CMiner info:
        - s <support> lines
        - f <frequency> lines
        - info: blocks
        - ---------- separators

        Returns structured PatternResult objects.
        """
        results: list[PatternResult] = []
        current_graph: nx.MultiDiGraph | None = None
        current_result: PatternResult | None = None
        in_info_block = False
        info_lines: list[str] = []

        for line in text.splitlines():
            stripped = line.strip()

            # separator or empty
            if stripped.startswith("----------") or not stripped:
                if in_info_block and current_result is not None:
                    current_result.info = "\n".join(info_lines)
                    in_info_block = False
                    info_lines = []
                continue

            # info block start
            if stripped == "info:":
                in_info_block = True
                info_lines = []
                continue

            # inside info block collect raw lines
            if in_info_block:
                info_lines.append(stripped)
                continue

            parts = stripped.split()
            tag = parts[0]

            # new graph
            if tag == "t":
                # save previous
                if current_result is not None:
                    results.append(current_result)
                current_graph = nx.MultiDiGraph()
                if len(parts) >= 3:
                    current_graph.graph["graph_index"] = parts[2]
                if len(parts) >= 4:
                    current_graph.graph["model_id"] = " ".join(parts[3:])
                current_result = PatternResult(graph=current_graph)

            # vertex
            elif tag == "v" and current_graph is not None:
                idx = int(parts[1])
                vtype = parts[2] if len(parts) > 2 else "unknown"
                current_graph.add_node(
                    idx,
                    id=str(idx),
                    type=vtype,
                    label=vtype,
                )

            # edge
            elif tag == "e" and current_graph is not None:
                src = int(parts[1])
                tgt = int(parts[2])
                etype = parts[3] if len(parts) > 3 else "unknown"
                current_graph.add_edge(src, tgt, type=etype, label=etype)

            # support
            elif tag == "s" and current_result is not None:
                try:
                    current_result.support = float(parts[1])
                except (IndexError, ValueError):
                    pass

            # frequency
            elif tag == "f" and current_result is not None:
                try:
                    current_result.frequency = float(parts[1])
                except (IndexError, ValueError):
                    pass

        # last pattern
        if current_result is not None:
            if in_info_block:
                current_result.info = "\n".join(info_lines)
            results.append(current_result)

        return results

    def parse_patterns_file(self, path: str | Path) -> list[PatternResult]:
        return self.parse_patterns(Path(path).read_text(encoding="utf-8"))


    @staticmethod
    def _render_one(graph: nx.MultiDiGraph, index: int) -> str:
        model_id = graph.graph.get("model_id", str(index))
        lines: list[str] = [f"t # {index} {model_id}"]

        idx_of: dict = {}
        for idx, (nid, d) in enumerate(graph.nodes(data=True)):
            idx_of[nid] = idx
            ntype = d.get("type") or d.get("label") or "unknown"
            lines.append(f"v {idx} {ntype}")

        for u, v, _k, d in graph.edges(keys=True, data=True):
            etype = d.get("type") or d.get("label") or "unknown"
            lines.append(f"e {idx_of[u]} {idx_of[v]} {etype}")

        return "\n".join(lines) + "\n"









