# Quick Start: Project Filter UI Tests

**For**: frontend-ux-expert agent  
**Task**: Implement project filter UI and enable tests

---

## 🚀 Quick Start (5 minutes)

### 1. Run Tests to See Current State

```bash
cd /Users/shehral/continuum-projects/apps/web
pnpm test knowledge-graph.test.tsx
```

You'll see: **23 passing, 29 skipped** ⏸️

---

## 📝 Implementation Checklist

### Step 1: Update Props Interface

In `components/graph/knowledge-graph.tsx`:

```typescript
interface KnowledgeGraphProps {
  data?: GraphData
  onNodeClick?: (node: Node) => void
  sourceFilter?: string | null
  onSourceFilterChange?: (source: string | null) => void
  sourceCounts?: Record<string, number>
  onDeleteDecision?: (decisionId: string) => Promise<void>
  
  // NEW: Add these props
  projectCounts?: Record<string, number>       // { continuum: 42, unassigned: 5 }
  projectFilter?: string | null                // Currently selected project
  onProjectFilterChange?: (project: string | null) => void
}
```

### Step 2: Add Project Filter Panel

Copy the source filter panel structure and adapt it:

```tsx
{/* Project Filter Panel - positioned below Source Filter */}
{projectCounts && Object.keys(projectCounts).length > 0 && (
  <Panel position="top-left" className={`m-4 ${showSourceLegend ? "mt-[280px]" : ""}`}>
    <Card className="w-56 bg-slate-800/90 backdrop-blur-xl border-white/10">
      <CardHeader className="py-3 px-4">
        <CardTitle className="text-sm text-slate-200">
          Projects
        </CardTitle>
      </CardHeader>
      <CardContent className="py-2 px-4 space-y-1.5">
        {/* "All Projects" button */}
        <button
          onClick={() => onProjectFilterChange?.(null)}
          aria-pressed={!projectFilter}
          aria-label="Show all projects"
          className={`w-full flex items-center gap-2 px-2 py-1.5 rounded-lg ${
            !projectFilter ? "bg-white/10 border border-white/20" : "hover:bg-white/5"
          }`}
        >
          <span className="text-xs text-slate-300 flex-1 text-left">All Projects</span>
          <Badge className="text-[9px] px-1.5 py-0 bg-slate-700 text-slate-300">
            {Object.values(projectCounts).reduce((a, b) => a + b, 0)}
          </Badge>
        </button>

        {/* Individual project buttons */}
        {Object.entries(projectCounts).map(([projectName, count]) => (
          <button
            key={projectName}
            onClick={() => onProjectFilterChange?.(
              projectFilter === projectName ? null : projectName
            )}
            aria-pressed={projectFilter === projectName}
            aria-label={`Filter by project ${projectName}`}
            className={`w-full flex items-center gap-2 px-2 py-1.5 rounded-lg ${
              projectFilter === projectName
                ? "bg-white/10 border border-white/20"
                : "hover:bg-white/5"
            }`}
          >
            <span className="text-xs text-slate-300 flex-1 text-left truncate">
              {projectName}
            </span>
            <Badge className="text-[9px] px-1.5 py-0 bg-slate-700 text-slate-300">
              {count}
            </Badge>
          </button>
        ))}
      </CardContent>
    </Card>
  </Panel>
)}
```

### Step 3: Update Parent Component (Graph Page)

Fetch project counts and handle state:

```tsx
// In app/graph/page.tsx or wherever KnowledgeGraph is used
const [projectFilter, setProjectFilter] = useState<string | null>(null)
const { data: projectCounts } = useQuery({
  queryKey: ['project-counts'],
  queryFn: () => api.getProjectCounts(),
})

// Pass to getGraph query
const { data: graphData } = useQuery({
  queryKey: ['graph', sourceFilter, projectFilter],
  queryFn: () => api.getGraph({
    source_filter: sourceFilter,
    project_filter: projectFilter,
    // ... other options
  }),
})

// Render
<KnowledgeGraph
  data={graphData}
  sourceFilter={sourceFilter}
  onSourceFilterChange={setSourceFilter}
  sourceCounts={sourceCounts}
  projectCounts={projectCounts}
  projectFilter={projectFilter}
  onProjectFilterChange={setProjectFilter}
/>
```

---

## 🧪 Enable Tests One by One

### Test 1: Basic Rendering

Remove `.skip()` from first test:

```typescript
// Before
it.skip('renders project filter panel when projectCounts provided', () => {

// After  
it('renders project filter panel when projectCounts provided', () => {
```

Run test:
```bash
pnpm test knowledge-graph.test.tsx -t "renders project filter panel"
```

If it passes ✅, move to next test.  
If it fails ❌, check implementation and fix.

### Test 2-6: Continue Enabling

Remove `.skip()` from tests in this order:
1. Rendering tests (6 tests)
2. Interaction tests (4 tests)
3. Visual highlighting (3 tests)
4. Accessibility (4 tests)
5. Integration (3 tests)
6. Edge cases (5 tests)
7. Position (2 tests)
8. Performance (2 tests)

---

## ✅ Success Criteria

All tests passing:
```
Test Files  3 passed (3)
Tests       93 passed (93)  ← No skipped tests!
```

---

## 🐛 Debugging Tips

### Test fails: "Unable to find element"
→ Check if you're rendering the panel conditionally based on `projectCounts`

### Test fails: "aria-pressed not set"
→ Add `aria-pressed={projectFilter === projectName}` to buttons

### Test fails: "onProjectFilterChange not called"
→ Check if you're calling the callback with correct arguments:
  - `null` for "All Projects"
  - `projectName` for individual projects
  - Toggle logic: `projectFilter === projectName ? null : projectName`

### Test fails: "Total count incorrect"
→ Verify you're summing counts: `Object.values(projectCounts).reduce((a, b) => a + b, 0)`

---

## 📊 Test Coverage

After enabling all tests, run coverage:

```bash
pnpm test:coverage
```

Target: **80%+ coverage** for `knowledge-graph.tsx`

---

## 🎯 Expected Timeline

- **Step 1**: Update props (5 min)
- **Step 2**: Implement panel UI (30 min)
- **Step 3**: Wire up state (15 min)
- **Enable tests**: Enable gradually while implementing (ongoing)
- **Fix issues**: Debug any failing tests (30 min)

**Total**: 1.5-2 hours

---

## 📚 Reference

**Test File**: `apps/web/__tests__/components/graph/knowledge-graph.test.tsx`  
**Full Review**: `docs/reviews/phase-2-qa-test-report.md`  
**Task List**: `docs/initiatives/2026-02-project-management/tasks/qa-tasks.md`

---

## 💡 Pro Tips

1. **Use watch mode**: `pnpm test --watch` for instant feedback
2. **Enable one test at a time**: Don't remove all `.skip()` at once
3. **Check existing source filter**: Use it as a reference for implementation
4. **Test accessibility**: Use keyboard (Tab, Enter) to verify navigation
5. **Check console**: No React warnings should appear

---

**Good luck!** 🚀

All tests are well-documented with clear expectations. If you get stuck, read the test assertions - they tell you exactly what the UI should do.

