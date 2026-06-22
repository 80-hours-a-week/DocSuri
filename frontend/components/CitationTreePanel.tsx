'use client';

import { useCallback, useEffect, useRef, useState } from 'react';
import { getApiClient } from '@/lib/api';
import type { CitationNode, CitationTreeResponse } from '@/types/citationGraph';
import styles from './CitationTreePanel.module.css';

interface CitationTreePanelProps {
  paperId: string;
  onClose?: () => void;
}

type LoadState =
  | { kind: 'loading' }
  | { kind: 'done'; tree: CitationTreeResponse }
  | { kind: 'error'; message: string };

export function CitationTreePanel({ paperId, onClose }: CitationTreePanelProps) {
  const [state, setState] = useState<LoadState>({ kind: 'loading' });
  const [expanded, setExpanded] = useState<Record<string, CitationTreeResponse>>({});
  const [expanding, setExpanding] = useState<string | null>(null);
  const [saved, setSaved] = useState<Set<string>>(() => new Set());
  const [saving, setSaving] = useState<string | null>(null);
  const [actionError, setActionError] = useState<string | null>(null);
  const panelRef = useRef<HTMLElement | null>(null);

  const load = useCallback(
    async (refresh = false) => {
      setState({ kind: 'loading' });
      setActionError(null);
      try {
        const tree = await getApiClient().getCitationTree(paperId, { refresh });
        setState({ kind: 'done', tree });
        if (refresh) setExpanded({});
      } catch {
        setState({ kind: 'error', message: '인용 트리를 불러오지 못했습니다.' });
      }
    },
    [paperId],
  );

  useEffect(() => {
    void load(false);
  }, [load]);

  useEffect(() => {
    const onKey = (event: KeyboardEvent) => {
      if (event.key === 'Escape') onClose?.();
    };
    document.addEventListener('keydown', onKey);
    const prevOverflow = document.body.style.overflow;
    document.body.style.overflow = 'hidden';
    panelRef.current?.focus();
    return () => {
      document.removeEventListener('keydown', onKey);
      document.body.style.overflow = prevOverflow;
    };
  }, [onClose]);

  async function expand(nodeId: string) {
    setExpanding(nodeId);
    setActionError(null);
    try {
      const tree = await getApiClient().getCitationTree(paperId, { expandNodeId: nodeId });
      setExpanded((prev) => ({ ...prev, [nodeId]: tree }));
    } catch {
      setActionError('선택한 인용의 하위 트리를 불러오지 못했습니다.');
    } finally {
      setExpanding(null);
    }
  }

  async function save(node: CitationNode) {
    setSaving(node.nodeId);
    setActionError(null);
    try {
      await getApiClient().saveCitationNode(paperId, node);
      setSaved((prev) => new Set(prev).add(node.nodeId));
    } catch {
      setActionError('라이브러리에 저장하지 못했습니다.');
    } finally {
      setSaving(null);
    }
  }

  return (
    <div className={styles.backdrop} onClick={onClose} data-testid="citation-tree-backdrop">
      <section
        ref={panelRef}
        className={styles.panel}
        role="dialog"
        aria-modal="true"
        aria-label="각주 트리"
        tabIndex={-1}
        onClick={(event) => event.stopPropagation()}
        data-testid="citation-tree-panel"
      >
      <div className={styles.header}>
        <div>
          <h2 className={styles.title}>각주 트리</h2>
          {state.kind === 'done' ? <TreeMeta tree={state.tree} /> : null}
        </div>
        <div className={styles.tools}>
          <button
            type="button"
            className={styles.secondary}
            onClick={() => void load(true)}
            disabled={state.kind === 'loading'}
          >
            새로고침
          </button>
          {onClose ? (
            <button
              type="button"
              className={styles.close}
              onClick={onClose}
              aria-label="닫기"
              data-testid="citation-tree-close"
            >
              ✕
            </button>
          ) : null}
        </div>
      </div>

      {state.kind === 'loading' ? (
        <p className={styles.message}>인용 관계를 불러오는 중...</p>
      ) : state.kind === 'error' ? (
        <p className={styles.error} role="alert">
          {state.message}
        </p>
      ) : (
        <>
          {state.tree.status === 'RateLimited' || state.tree.status === 'Unavailable' ? (
            <p className={styles.error} role="status">
              현재 제공자가 응답하지 않아 일부 인용 정보를 표시할 수 없습니다.
            </p>
          ) : null}
          {actionError ? (
            <p className={styles.error} role="alert">
              {actionError}
            </p>
          ) : null}
          <ul className={styles.tree}>
            {state.tree.nodes.map((node, index) => (
              <TreeNode
                key={node.nodeId}
                node={node}
                prefix=""
                isLast={index === state.tree.nodes.length - 1}
                expandedById={expanded}
                expanding={expanding === node.nodeId}
                savedIds={saved}
                savingId={saving}
                onExpand={expand}
                onSave={save}
              />
            ))}
          </ul>
          {state.tree.unresolved.length > 0 ? (
            <div>
              <p className={styles.meta}>해결되지 않은 인용</p>
              <ul className={styles.unresolved}>
                {state.tree.unresolved.map((item) => (
                  <li key={item}>{item}</li>
                ))}
              </ul>
            </div>
          ) : null}
        </>
      )}
      </section>
    </div>
  );
}

function TreeMeta({ tree }: { tree: CitationTreeResponse }) {
  const more = tree.truncated && tree.remainingEstimate ? ` · 남은 예상 ${tree.remainingEstimate}건` : '';
  return (
    <p className={styles.meta}>
      {tree.status} · depth {tree.depthReturned} · {tree.cacheHit ? '캐시 사용' : '신규 조회'}
      {more}
    </p>
  );
}

function TreeNode({
  node,
  prefix,
  isLast,
  expandedById,
  expanding,
  savedIds,
  savingId,
  onExpand,
  onSave,
}: {
  node: CitationNode;
  prefix: string;
  isLast: boolean;
  expandedById: Record<string, CitationTreeResponse>;
  expanding: boolean;
  savedIds: Set<string>;
  savingId: string | null;
  onExpand: (nodeId: string) => void;
  onSave: (node: CitationNode) => void;
}) {
  const year = node.year ? String(node.year) : '연도 미상';
  const citations = typeof node.citationCount === 'number' ? `${node.citationCount.toLocaleString()}회 인용` : '인용수 미상';
  const expanded = expandedById[node.nodeId];
  const saved = savedIds.has(node.nodeId);
  const saving = savingId === node.nodeId;
  const childPrefix = `${prefix}${isLast ? '    ' : '│   '}`;
  const childNodes = expanded?.nodes ?? [];

  return (
    <li className={styles.node}>
      <div className={styles.nodeMain}>
        <span className={styles.branch} aria-hidden="true">
          {prefix}
          {isLast ? '└── ' : '├── '}
        </span>
        <div className={styles.nodeText}>
          <div>
            <p className={styles.nodeTitle}>{node.title}</p>
            <div className={styles.nodeMeta}>
              <span>{year}</span>
              <span>{citations}</span>
              {node.alreadyShown ? <span>이미 표시됨</span> : null}
            </div>
          </div>
          <div className={styles.nodeActions}>
            <button
              type="button"
              className={styles.button}
              onClick={() => onExpand(node.nodeId)}
              disabled={expanding}
              data-testid={`citation-expand-${node.nodeId}`}
            >
              {expanding ? '확장 중' : expanded ? '다시 확장' : '확장'}
            </button>
            <button
              type="button"
              className={styles.button}
              onClick={() => onSave(node)}
              disabled={!node.saveable || saving || saved}
              data-testid={`citation-save-${node.nodeId}`}
            >
              {saved ? '저장됨' : saving ? '저장 중' : node.saveable ? '저장' : '저장 불가'}
            </button>
          </div>
        </div>
      </div>
      {expanded ? (
        <ul className={styles.tree}>
          {childNodes.map((child, index) => (
            <TreeNode
              key={child.nodeId}
              node={child}
              prefix={childPrefix}
              isLast={index === childNodes.length - 1}
              expandedById={expandedById}
              expanding={false}
              savedIds={savedIds}
              savingId={savingId}
              onExpand={onExpand}
              onSave={onSave}
            />
          ))}
        </ul>
      ) : null}
    </li>
  );
}
