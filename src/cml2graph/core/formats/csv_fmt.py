import csv
import io
from pathlib import Path

import networkx as nx


class CsvFormat:
    """CSV codec for a nx graph."""

    @property
    def format_name(self) -> str:
        return "csv"

    def render_corpus(
        self,
        graphs: dict[str, nx.MultiDiGraph],
        output_dir: Path,
        sep: str = ",",
        label_sep: str = ",",
    ) -> None:
        """
        Write the directory structure the consumer expects::

            output_dir/
            └── <graph_name>/
                ├── nodes/
                │   └── nodes.csv    (id, labels)
                └── edges/
                    └── edges.csv    (source, target, type, ...)
        """
        for name, g in graphs.items():
            graph_dir = output_dir / name
            nodes_dir = graph_dir / "nodes"
            edges_dir = graph_dir / "edges"
            nodes_dir.mkdir(parents=True, exist_ok=True)
            edges_dir.mkdir(parents=True, exist_ok=True)

            # Nodes
            with open(nodes_dir / "nodes.csv", "w", newline="") as f:
                w = csv.writer(f, delimiter=sep)
                w.writerow(["id", "labels"])
                for nid, d in g.nodes(data=True):
                    labels = label_sep.join(
                        filter(None, [d.get("type", ""), d.get("label", "")])
                    )
                    w.writerow([nid, labels])

            # Edges
            with open(edges_dir / "edges.csv", "w", newline="") as f:
                w = csv.writer(f, delimiter=sep)
                w.writerow(["source", "target", "type"])
                for u, v, _k, d in g.edges(keys=True, data=True):
                    w.writerow([u, v, d.get("type", "")])

    def render(self, graph: nx.MultiDiGraph) -> str:
        """Single-graph render to string (nodes section + edges section)."""
        buf = io.StringIO()
        buf.write("# nodes: id,type,label\n")
        for nid, d in graph.nodes(data=True):
            buf.write(f"{nid},{d.get('type','')},{d.get('label','')}\n")
        buf.write("# edges: source,target,type\n")
        for u, v, _k, d in graph.edges(keys=True, data=True):
            buf.write(f"{u},{v},{d.get('type','')}\n")
        return buf.getvalue()