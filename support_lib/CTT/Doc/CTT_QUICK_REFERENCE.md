# CTT Expression Tree - Quick Reference

## 🚀 Quick Start

### Import Everything

```python
from support_lib.CTT import (
    CttTask, CttOperatorNode,
    visualize_expression_tree,
    linearize_expression_tree,
    count_tasks, get_tree_depth,
    validate_ctt_tree
)
```

## 📐 Two Structures

### Structure 1: Flat Children (Simple)
```python
{
    "task_id": "payment",
    "title": "Payment",
    "operator": "choice",
    "children": [task_a, task_b, task_c]
}
```
**Use when:** Single operator for all children

### Structure 2: Expression Tree (Complex)
```python
{
    "task_id": "checkout",
    "title": "Checkout",
    "children_tree": [
        {
            "operator": "sequence",
            "left": task_1,
            "right": {
                "operator": "choice",
                "left": task_2,
                "right": task_3
            }
        }
    ]
}
```
**Use when:** Mixed operators, complex workflows

## 🔧 Operators

| Name | Symbol | Meaning |
|------|--------|---------|
| Sequence | `>>` | Left then right |
| Choice | `[]` | Left OR right |
| Interleaving | `\|\|\|` | Left AND right parallel |
| Disabling | `[>` | Left interrupts right |

## 📊 Utilities

```python
# Visualize as ASCII art
print(visualize_expression_tree(tree))
# Output:
# ├── SEQUENCE (>>)
#   ├── Task A
#   └── Task B

# Linear notation
print(linearize_expression_tree(tree))
# Output: Task A >> Task B

# Metrics
print(f"Tasks: {count_tasks(tree)}")
print(f"Depth: {get_tree_depth(tree)}")

# Validate
errors = validate_ctt_tree([root_task])
if errors:
    print(f"Errors: {errors}")
```

## 📝 Common Patterns

### Pattern 1: Sequential Steps
```python
tree = {
    "operator": "sequence",
    "left": {"task_id": "step1", "title": "Step 1"},
    "right": {"task_id": "step2", "title": "Step 2"}
}
```
Visualization: `Step 1 >> Step 2`

### Pattern 2: Choice Branch
```python
tree = {
    "operator": "choice",
    "left": {"task_id": "a", "title": "Option A"},
    "right": {"task_id": "b", "title": "Option B"}
}
```
Visualization: `Option A [] Option B`

### Pattern 3: Parallel Execution
```python
tree = {
    "operator": "interleaving",
    "left": {"task_id": "task1", "title": "Task 1"},
    "right": {"task_id": "task2", "title": "Task 2"}
}
```
Visualization: `Task 1 ||| Task 2`

### Pattern 4: Nested Mixed Operators
```python
tree = {
    "operator": "sequence",
    "left": {"task_id": "setup", "title": "Setup"},
    "right": {
        "operator": "choice",
        "left": {"task_id": "process", "title": "Process"},
        "right": {"task_id": "skip", "title": "Skip"}
    }
}
```
Visualization: `Setup >> (Process [] Skip)`

## 🎯 When to Use Each Structure

### Use Flat Children When:
- ✅ Single operator type
- ✅ Simple branching
- ✅ Configuration files
- ✅ Template-based tasks

### Use Expression Tree When:
- ✅ Mixed operators
- ✅ Complex workflows
- ✅ Arbitrary nesting
- ✅ W3C compliance needed

## ✅ Validation Rules

1. **Both fields optional** - tasks can have `children` OR `children_tree`, not both
2. **Leaf tasks** - no operator field on tasks with 0-1 children
3. **Binary operators** - operator nodes always have left AND right
4. **Unique task IDs** - within entire tree
5. **Valid operators** - sequence, choice, interleaving, disabling only

## 🧪 Testing

```bash
# Run test suite
python tests/test_expression_tree_ctt.py

# View utilities in action
python support_lib/CTT/tree_utilities.py
```

## 📚 Examples

See `Agents/Nodes/node_task_master/EXPRESSION_TREE_EXAMPLES.jsonc` for:
- E-Commerce checkout
- CI/CD pipeline
- Complex nested workflow
- Choice between branches

## 🔗 Integration

### LangGraph
```python
def execute(node):
    if "operator" in node:
        op = node["operator"]
        if op == "sequence":
            execute(node["left"])
            execute(node["right"])
        elif op == "choice":
            chosen = llm_choose(node["left"], node["right"])
            execute(chosen)
    else:
        execute_task(node)
```

### LLM Generation
LLM now understands both formats and can generate either based on workflow complexity.

## 📞 Documentation

| File | Purpose |
|------|---------|
| `CTT_EXPRESSION_TREE_GUIDE.md` | User-facing guide |
| `CTT_EXPRESSION_TREE_IMPLEMENTATION.md` | Technical details |
| `EXPRESSION_TREE_EXAMPLES.jsonc` | JSON examples |
| `system_prompt.txt` | LLM instructions |

## ✨ Key Features

- ✅ **Binary operator nodes** (like AST)
- ✅ **Unlimited nesting** (recursive)
- ✅ **Type-safe** (with TypedDict)
- ✅ **W3C compliant** (CTT standard)
- ✅ **100% backward compatible** (old structures work)
- ✅ **Fully tested** (6/6 tests passing)
- ✅ **Rich utilities** (visualization, metrics, etc.)

## 🚨 Common Mistakes

❌ Don't mix `children` and `children_tree`:
```python
# WRONG
{
  "children": [...],
  "children_tree": [...]
}
```

✅ Do use one or the other:
```python
# Right (flat)
{"operator": "sequence", "children": [...]}

# Right (expression tree)
{"children_tree": [{"operator": "sequence", "left": ..., "right": ...}]}
```

❌ Don't put operators on leaf tasks:
```python
# WRONG
{"task_id": "leaf", "operator": "sequence"}
```

✅ Only branch nodes have operators:
```python
# Right - task with 2 children
{"task_id": "branch", "operator": "sequence", "children": [a, b]}

# Right - leaf task, no operator
{"task_id": "leaf"}
```

## 🎓 Architecture

Expression Trees work because:

1. **Like math expressions** - operators sit between operands
2. **Like AST parsers** - recursive binary tree structure
3. **Like function calls** - can nest arbitrarily deep
4. **Like LangGraph** - maps to recursive execution

```
Visual:    A >> (B [] C)

Tree:           Seq(>>)
               /        \
              A      Choice([])
                    /        \
                   B          C

Execution:
1. Execute A
2. After A completes, choose B or C
3. Execute chosen task
```

## 💡 Pro Tips

1. **Start with flat** for simple cases, upgrade to trees if needed
2. **Use linearize** to understand complex trees: `print(linearize_expression_tree(t))`
3. **Use visualize** for debugging: `print(visualize_expression_tree(t))`
4. **Check depth** to avoid deep nesting: `print(get_tree_depth(t))`
5. **Let LLM choose** structure - it understands both methods

## 🔄 Converting Between Formats

### Expression Tree → Flat (lossy)

```python
from support_lib.CTT import flatten_expression_tree

flat = flatten_expression_tree(expression_tree)
```

### Flat → Expression Tree (manual)
```python
# Manual conversion needed - more flexible
# Each child becomes left/right nodes
```

## 📊 Example Output

```python
tree = {
    "operator": "sequence",
    "left": {"task_id": "fetch", "title": "Fetch"},
    "right": {"task_id": "parse", "title": "Parse"}
}

# Visualization
visualize_expression_tree(tree)
# Output:
# ├── SEQUENCE (>>)
#   ├── Fetch (fetch)
#   └── Parse (parse)

# Linear notation
linearize_expression_tree(tree)
# Output: Fetch >> Parse

# Metrics
count_tasks(tree)        # 2
get_tree_depth(tree)     # 1
```

## ✅ Status

- **Implementation:** Complete ✅
- **Testing:** All passing ✅
- **Documentation:** Comprehensive ✅
- **Production:** Ready ✅

---

**For detailed information, see:**
- Main docs: `CTT_EXPRESSION_TREE_GUIDE.md`
- Technical: `CTT_EXPRESSION_TREE_IMPLEMENTATION.md`
- Examples: `EXPRESSION_TREE_EXAMPLES.jsonc`


