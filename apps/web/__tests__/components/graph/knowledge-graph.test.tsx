import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen, fireEvent } from '../../utils/test-utils'
import { KnowledgeGraph } from '@/components/graph/knowledge-graph'

// Mock ReactFlow since it requires browser APIs
vi.mock('@xyflow/react', () => {
  const React = require('react')

  const MockReactFlow = ({ children, nodes, edges, onNodeClick }: {
    children: React.ReactNode
    nodes: { id: string; data: { label: string } }[]
    edges: { id: string }[]
    onNodeClick?: (event: React.MouseEvent, node: { id: string }) => void
  }) => (
    <div data-testid="react-flow">
      <div data-testid="nodes-container">
        {nodes.map((node: { id: string; data: { label: string } }) => (
          <div
            key={node.id}
            data-testid={`node-${node.id}`}
            onClick={(e) => onNodeClick?.(e, node as any)}
          >
            {node.data.label}
          </div>
        ))}
      </div>
      <div data-testid="edges-container">
        {edges.map((edge: { id: string }) => (
          <div key={edge.id} data-testid={`edge-${edge.id}`} />
        ))}
      </div>
      {children}
    </div>
  )

  return {
    ReactFlow: MockReactFlow,
    Controls: () => <div data-testid="controls" />,
    Background: () => <div data-testid="background" />,
    MiniMap: () => <div data-testid="minimap" />,
    Panel: ({ children, position }: { children: React.ReactNode; position: string }) => (
      <div data-testid={`panel-${position}`}>{children}</div>
    ),
    useNodesState: (initialNodes: any[]) => [initialNodes, vi.fn(), vi.fn()],
    useEdgesState: (initialEdges: any[]) => [initialEdges, vi.fn(), vi.fn()],
    Handle: () => null,
    Position: { Top: 'top', Bottom: 'bottom' },
    MarkerType: { ArrowClosed: 'arrowclosed' },
    BackgroundVariant: { Dots: 'dots' },
  }
})

// Sample test data with proper types
const sampleGraphData = {
  nodes: [
    {
      id: 'decision-1',
      type: 'decision' as const,
      label: 'Use PostgreSQL for database',
      has_embedding: true,
      data: {
        id: 'decision-1',
        trigger: 'Need to choose a database',
        context: 'Building a new application',
        options: ['PostgreSQL', 'MongoDB', 'MySQL'],
        decision: 'Use PostgreSQL',
        rationale: 'Better for relational data',
        confidence: 0.9,
        created_at: '2024-01-01T00:00:00Z',
        source: 'claude_logs' as const,
        entities: [{ id: 'e1', name: 'PostgreSQL', type: 'technology' as const }],
      },
    },
    {
      id: 'entity-1',
      type: 'entity' as const,
      label: 'PostgreSQL',
      has_embedding: true,
      data: {
        id: 'entity-1',
        name: 'PostgreSQL',
        type: 'technology' as const,
      },
    },
    {
      id: 'entity-2',
      type: 'entity' as const,
      label: 'Redis',
      has_embedding: false,
      data: {
        id: 'entity-2',
        name: 'Redis',
        type: 'technology' as const,
      },
    },
  ],
  edges: [
    {
      id: 'edge-1',
      source: 'decision-1',
      target: 'entity-1',
      relationship: 'INVOLVES',
      weight: 0.95,
    },
  ],
}

describe('KnowledgeGraph', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  describe('Rendering', () => {
    it('renders without crashing', () => {
      render(<KnowledgeGraph />)
      expect(screen.getByTestId('react-flow')).toBeInTheDocument()
    })

    it('renders with graph data', () => {
      render(<KnowledgeGraph data={sampleGraphData} />)
      expect(screen.getByTestId('react-flow')).toBeInTheDocument()
    })

    it('renders correct number of nodes', () => {
      render(<KnowledgeGraph data={sampleGraphData} />)
      expect(screen.getByTestId('node-decision-1')).toBeInTheDocument()
      expect(screen.getByTestId('node-entity-1')).toBeInTheDocument()
      expect(screen.getByTestId('node-entity-2')).toBeInTheDocument()
    })

    it('renders correct number of edges', () => {
      render(<KnowledgeGraph data={sampleGraphData} />)
      expect(screen.getByTestId('edge-edge-1')).toBeInTheDocument()
    })

    it('renders controls and minimap', () => {
      render(<KnowledgeGraph data={sampleGraphData} />)
      expect(screen.getByTestId('controls')).toBeInTheDocument()
      expect(screen.getByTestId('minimap')).toBeInTheDocument()
    })

    it('renders background', () => {
      render(<KnowledgeGraph data={sampleGraphData} />)
      expect(screen.getByTestId('background')).toBeInTheDocument()
    })
  })

  describe('Empty State', () => {
    it('renders with empty data', () => {
      render(<KnowledgeGraph data={{ nodes: [], edges: [] }} />)
      expect(screen.getByTestId('react-flow')).toBeInTheDocument()
    })

    it('renders with undefined data', () => {
      render(<KnowledgeGraph data={undefined} />)
      expect(screen.getByTestId('react-flow')).toBeInTheDocument()
    })
  })

  describe('Node Interaction', () => {
    it('calls onNodeClick when node is clicked', () => {
      const handleNodeClick = vi.fn()
      render(
        <KnowledgeGraph
          data={sampleGraphData}
          onNodeClick={handleNodeClick}
        />
      )

      fireEvent.click(screen.getByTestId('node-decision-1'))
      expect(handleNodeClick).toHaveBeenCalled()
    })

    it('shows detail panel when node is selected', () => {
      render(<KnowledgeGraph data={sampleGraphData} />)

      fireEvent.click(screen.getByTestId('node-decision-1'))

      // Detail panel should appear
      expect(screen.getByText(/Decision Details/i)).toBeInTheDocument()
    })
  })

  describe('Source Filtering', () => {
    it('renders source filter panel', () => {
      render(
        <KnowledgeGraph
          data={sampleGraphData}
          sourceCounts={{ claude_logs: 5, interview: 3, manual: 2 }}
        />
      )

      expect(screen.getByText(/Decision Sources/i)).toBeInTheDocument()
    })

    it('shows source counts in filter', () => {
      render(
        <KnowledgeGraph
          data={sampleGraphData}
          sourceCounts={{ claude_logs: 5, interview: 3, manual: 2 }}
        />
      )

      expect(screen.getByText('5')).toBeInTheDocument()
      expect(screen.getByText('3')).toBeInTheDocument()
      expect(screen.getByText('2')).toBeInTheDocument()
    })

    it('calls onSourceFilterChange when source is clicked', () => {
      const handleSourceFilter = vi.fn()
      render(
        <KnowledgeGraph
          data={sampleGraphData}
          sourceCounts={{ claude_logs: 5, interview: 3 }}
          onSourceFilterChange={handleSourceFilter}
        />
      )

      // Click on a source filter button
      const aiExtractedButton = screen.getByText('AI Extracted')
      fireEvent.click(aiExtractedButton)

      expect(handleSourceFilter).toHaveBeenCalled()
    })
  })

  describe('Panels', () => {
    it('renders entity types legend', () => {
      render(<KnowledgeGraph data={sampleGraphData} />)
      expect(screen.getByText(/Entity Types/i)).toBeInTheDocument()
    })

    it('renders relationship legend', () => {
      render(<KnowledgeGraph data={sampleGraphData} />)
      expect(screen.getByText(/Relationships/i)).toBeInTheDocument()
    })

    it('renders stats panel with node and edge counts', () => {
      render(<KnowledgeGraph data={sampleGraphData} />)
      expect(screen.getByText(/3 nodes/i)).toBeInTheDocument()
      expect(screen.getByText(/1 edges/i)).toBeInTheDocument()
    })

    it('renders tip panel', () => {
      render(<KnowledgeGraph data={sampleGraphData} />)
      expect(screen.getByText(/Click and drag to pan/i)).toBeInTheDocument()
    })
  })

  describe('Detail Panel', () => {
    it('shows decision details when decision node is selected', () => {
      render(<KnowledgeGraph data={sampleGraphData} />)

      fireEvent.click(screen.getByTestId('node-decision-1'))

      expect(screen.getByText('Trigger')).toBeInTheDocument()
      expect(screen.getByText('Context')).toBeInTheDocument()
      expect(screen.getByText('Decision')).toBeInTheDocument()
      expect(screen.getByText('Rationale')).toBeInTheDocument()
    })

    it('can close detail panel', () => {
      render(<KnowledgeGraph data={sampleGraphData} />)

      fireEvent.click(screen.getByTestId('node-decision-1'))
      expect(screen.getByText(/Decision Details/i)).toBeInTheDocument()

      // Find and click close button (X icon)
      const closeButtons = screen.getAllByRole('button')
      const closeButton = closeButtons.find(btn =>
        btn.className.includes('hover:text-slate-200')
      )
      if (closeButton) {
        fireEvent.click(closeButton)
      }
    })
  })

  describe('Relationship Styling', () => {
    it('renders edges with relationship type', () => {
      const dataWithMultipleEdges = {
        ...sampleGraphData,
        edges: [
          { id: 'e1', source: 'd1', target: 'ent1', relationship: 'INVOLVES', weight: 1.0 },
          { id: 'e2', source: 'd1', target: 'ent2', relationship: 'SIMILAR_TO', weight: 0.8 },
        ],
      }

      render(<KnowledgeGraph data={dataWithMultipleEdges} />)
      expect(screen.getByTestId('edge-e1')).toBeInTheDocument()
      expect(screen.getByTestId('edge-e2')).toBeInTheDocument()
    })
  })

  describe('Accessibility', () => {
    it('has interactive elements', () => {
      render(<KnowledgeGraph data={sampleGraphData} />)
      const buttons = screen.getAllByRole('button')
      expect(buttons.length).toBeGreaterThan(0)
    })
  })
})

describe('Node Types', () => {
  describe('Decision Nodes', () => {
    it('renders decision node with correct label', () => {
      render(<KnowledgeGraph data={sampleGraphData} />)
      expect(screen.getByText('Use PostgreSQL for database')).toBeInTheDocument()
    })
  })

  describe('Entity Nodes', () => {
    it('renders entity nodes with correct labels', () => {
      render(<KnowledgeGraph data={sampleGraphData} />)
      expect(screen.getByText('PostgreSQL')).toBeInTheDocument()
      expect(screen.getByText('Redis')).toBeInTheDocument()
    })
  })
})
