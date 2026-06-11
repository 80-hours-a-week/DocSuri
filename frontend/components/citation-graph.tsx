"use client";

// U4 CitationGraphView — 데스크톱 1-hop 그래프 (TRACE-01, ≤30 노드는 백엔드가 절단).
// 배치: 피인용(좌) → 중심 → 인용(우). 노드 내부는 <button>이라 클릭·키보드(Enter)
// 모두 동작 (NFR-A11Y-02), 최소 높이 44px (NFR-A11Y-03).

import { useMemo } from "react";
import {
  Background,
  Controls,
  Handle,
  MarkerType,
  Position,
  ReactFlow,
  type Edge,
  type Node,
  type NodeProps,
} from "@xyflow/react";
import "@xyflow/react/dist/style.css";

import type { CitationPaper, CitationView } from "@/lib/types";

type Role = "center" | "outgoing" | "incoming";

interface PaperNodeData extends Record<string, unknown> {
  paper: CitationPaper;
  role: Role;
  onOpen: (paper: CitationPaper) => void;
}

const ROLE_STYLE: Record<Role, string> = {
  center: "border-primary bg-primary/10 font-semibold",
  outgoing: "border-amber-300 bg-amber-50 dark:border-amber-800 dark:bg-amber-950",
  incoming: "border-emerald-300 bg-emerald-50 dark:border-emerald-800 dark:bg-emerald-950",
};

function PaperNode({ data }: NodeProps<Node<PaperNodeData>>) {
  const { paper, role, onOpen } = data;
  return (
    <div className={`w-60 rounded-lg border text-card-foreground shadow-sm ${ROLE_STYLE[role]}`}>
      <Handle type="target" position={Position.Left} className="opacity-0!" />
      <button
        type="button"
        className="block min-h-11 w-full rounded-lg p-2.5 text-left text-xs leading-snug"
        aria-label={`논문 카드 열기: ${paper.title}`}
        onClick={() => onOpen(paper)}
      >
        <span className="line-clamp-2 font-medium">{paper.title}</span>
        <span className="mt-1 block text-muted-foreground">
          {paper.year || "—"} · 인용 {paper.citations.toLocaleString("en-US")}
        </span>
      </button>
      <Handle type="source" position={Position.Right} className="opacity-0!" />
    </div>
  );
}

const nodeTypes = { paper: PaperNode };

const COL_X = 480;
const ROW_Y = 110;

export function CitationGraph({
  view,
  onOpenPaper,
}: {
  view: CitationView;
  onOpenPaper: (paper: CitationPaper) => void;
}) {
  const { nodes, edges } = useMemo(() => {
    const rows = Math.max(view.incoming.length, view.outgoing.length, 1);
    const centerY = ((rows - 1) * ROW_Y) / 2;

    const make = (paper: CitationPaper, role: Role, x: number, y: number): Node<PaperNodeData> => ({
      id: `${role}:${paper.id}`,
      type: "paper",
      position: { x, y },
      data: { paper, role, onOpen: onOpenPaper },
    });

    const nodes: Node<PaperNodeData>[] = [
      make(view.center, "center", 0, centerY),
      ...view.incoming.map((p, i) => make(p, "incoming", -COL_X, i * ROW_Y)),
      ...view.outgoing.map((p, i) => make(p, "outgoing", COL_X, i * ROW_Y)),
    ];

    const edges: Edge[] = [
      // 피인용(incoming): 후속 논문 → 중심
      ...view.incoming.map((p) => ({
        id: `e-in:${p.id}`,
        source: `incoming:${p.id}`,
        target: `center:${view.center.id}`,
        markerEnd: { type: MarkerType.ArrowClosed },
      })),
      // 인용(outgoing): 중심 → 참고 문헌
      ...view.outgoing.map((p) => ({
        id: `e-out:${p.id}`,
        source: `center:${view.center.id}`,
        target: `outgoing:${p.id}`,
        markerEnd: { type: MarkerType.ArrowClosed },
      })),
    ];
    return { nodes, edges };
  }, [view, onOpenPaper]);

  return (
    <div className="h-[62vh] w-full overflow-hidden rounded-xl border" data-testid="citation-graph">
      <ReactFlow
        nodes={nodes}
        edges={edges}
        nodeTypes={nodeTypes}
        fitView
        minZoom={0.25}
        nodesDraggable={false}
        nodesConnectable={false}
        edgesFocusable={false}
        proOptions={{ hideAttribution: false }}
      >
        <Background gap={24} />
        <Controls showInteractive={false} />
      </ReactFlow>
      <p className="sr-only">
        중심 논문과 인용·피인용 관계 그래프. 각 노드는 버튼이며 선택 시 논문 카드가 열립니다.
      </p>
    </div>
  );
}
