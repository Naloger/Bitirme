# CTT Expression Tree Support - User Guide

## Overview

The CTT (Concurrent Task Trees) library now supports **Expression Tree** structure for representing complex workflows where temporal operators sit **between** child tasks, exactly as shown in the W3C CTT specification diagrams.

## Two Approaches to Structure CTT Trees

### Approach 1: Flat Children (Simple, Traditional)

For straightforward workflows with a single operator applied to all children, use the **flat list** approach:

```python
{
  "task_id": "process_payment",
  "title": "Process Payment",
  "task_description": "Handle payment with multiple methods",
  "operator": "choice",  # Single operator for all children
  "children": [
    {
      "task_id": "cc_payment",
      "title": "Credit Card",
      "task_description": "Process credit card"
    },
    {
      "task_id": "paypal_payment",
      "title": "PayPal",
      "task_description": "Process via PayPal"
    },
    {
      "task_id": "bank_transfer",
      "title": "Bank Transfer",
      "task_description": "Process bank transfer"
    }
  ]
}
```

**JSON Structure:**
```json
{
  "operator": "choice",
  "children": [Task1, Task2, Task3]
}
```

**When to use:**
- Simple branching with one operator type
- All children are siblings with same relationship
- Legacy CTT systems

---

### Approach 2: Expression Tree (Recommended, W3C Standard)

For complex workflows where different operators appear **between** different pairs of tasks, use **expression tree** with binary operator nodes:

```python
{
  "task_id": "checkout",
  "title": "E-Commerce Checkout",
  "task_description": "Complete purchase workflow",
  "children_tree": [
    {
      "operator": "sequence",      # >> operator
      "left": {
        "task_id": "get_details",
        "title": "Get Customer Details",
        "task_description": "Collect customer information"
      },
      "right": {
        "operator": "choice",        # [] operator
        "left": {
          "task_id": "cc_payment",
          "title": "Credit Card",
          "task_description": "Charge credit card"
        },
        "right": {
          "task_id": "paypal_payment",
          "title": "PayPal",
          "task_description": "Use PayPal"
        }
      }
    }
  ]
}
```

**Visualized as:**
```
Get_Details >> (Process_Card [] Process_PayPal)
```

**Tree Structure:**
```
          Sequence (>>)
         /              \
   Get_Details      Choice ([])
                    /          \
              CC_Payment    PayPal_Payment
```

**When to use:**
- Mixed operators in same workflow (sequence, then choice, then parallel)
- Complex conditional flows
- W3C CTT compliance
- LangGraph integration
- More expressive task orchestration

---

## Expression Tree Semantics

### Binary Operator Nodes

Each operator node has exactly two children: `left` and `right`.

```python
class OperatorNode:
    operator: str                  # "sequence", "choice", "interleaving", etc.
    left: Task | OperatorNode     # Left subtree
    right: Task | OperatorNode    # Right subtree (can be another operator!)
```

### Key Rules

1. **Both left and right must be defined** - No null values
2. **Recursive nesting allowed** - right side can be another operator node
3. **Any node can be a task or operator** - Maximum flexibility
4. **Do NOT mix `children` and `children_tree`** - Use one or the other per task

---

## Real-World Examples

### Example 1: Simple Sequential Flow

**Use Case:** Web scraping steps

```python
{
  "task_id": "scrape",
  "title": "Web Scraper",
  "task_description": "Fetch and parse website",
  "children_tree": [
    {
      "operator": "sequence",
      "left": {
        "task_id": "fetch",
        "title": "Fetch Page",
        "task_description": "Download HTML"
      },
      "right": {
        "task_id": "parse",
        "title": "Parse HTML",
        "task_description": "Extract data"
      }
    }
  ]
}
```

**Visualization:** `Fetch >> Parse`

---

### Example 2: Sequence with Choice

**Use Case:** Error handling

```python
{
  "task_id": "data_processing",
  "title": "Process Data",
  "task_description": "Handle processing with error recovery",
  "children_tree": [
    {
      "operator": "sequence",
      "left": {
        "task_id": "validate",
        "title": "Validate Input",
        "task_description": "Check data integrity"
      },
      "right": {
        "operator": "choice",
        "left": {
          "task_id": "process_valid",
          "title": "Process Valid Data",
          "task_description": "Run processing pipeline"
        },
        "right": {
          "task_id": "handle_error",
          "title": "Handle Invalid Data",
          "task_description": "Log error and skip"
        }
      }
    }
  ]
}
```

**Visualization:** `Validate >> (Process [] HandleError)`

---

### Example 3: Complex Nested Operators

**Use Case:** CI/CD Pipeline

```python
{
  "task_id": "ci_cd",
  "title": "CI/CD Pipeline",
  "task_description": "Build, test, and deploy",
  "children_tree": [
    {
      "operator": "sequence",
      "left": {
        "task_id": "build",
        "title": "Build",
        "task_description": "Compile code"
      },
      "right": {
        "operator": "sequence",
        "left": {
          "operator": "interleaving",
          "left": {
            "task_id": "unit_tests",
            "title": "Unit Tests",
            "task_description": "Run unit tests",
            "iterative": True
          },
          "right": {
            "operator": "interleaving",
            "left": {
              "task_id": "integration_tests",
              "title": "Integration Tests",
              "task_description": "Run integration tests"
            },
            "right": {
              "task_id": "security_scan",
              "title": "Security Scan",
              "task_description": "Check for vulnerabilities"
            }
          }
        },
        "right": {
          "operator": "choice",
          "left": {
            "task_id": "deploy_prod",
            "title": "Deploy to Production",
            "task_description": "Push to production"
          },
          "right": {
            "task_id": "deploy_staging",
            "title": "Deploy to Staging",
            "task_description": "Push to staging"
          }
        }
      }
    }
  ]
}
```

**Visualization:**
```
Build >> ((UnitTests ||| (IntegrationTests ||| Security)) >> (DeployProd [] DeployStaging))
```

---

## Operators Reference

| Operator | Symbol | Meaning | Use When |
|----------|--------|---------|----------|
| `sequence` | `>>` | Execute left, then right | Tasks have dependencies |
| `choice` | `[]` | Execute either left OR right | Mutual exclusive branches |
| `interleaving` | `\|\|\|` | Execute left AND right in parallel | Tasks are independent |
| `disabling` | `[>` | Left can interrupt right | Priority-based execution |

---

## Parsing and Execution

### For LLM Orchestrators (LangGraph)

When an LLM executor traverses this tree:

```python
def execute_node(node):
    if isinstance(node, OperatorNode):
        operator = node.operator
        
        if operator == "sequence":
            result_left = execute_node(node.left)
            # Wait for completion
            result_right = execute_node(node.right)
            return result_right
            
        elif operator == "choice":
            context = get_context()  # LLM context
            chosen = llm_choose(node.left, node.right, context)
            return execute_node(chosen)
            
        elif operator == "interleaving":
            # Run both in parallel
            t1 = asyncio.create_task(execute_node(node.left))
            t2 = asyncio.create_task(execute_node(node.right))
            return asyncio.gather(t1, t2)
    else:
        # It's a task
        return execute_task(node)
```

### For JSON/YAML Config Files

Expression trees naturally serialize to JSON:

```json
{
  "root_tasks": [
    {
      "task_id": "root",
      "title": "Root Workflow",
      "task_description": "Complex workflow",
      "children_tree": [
        {
          "operator": "sequence",
          "left": {...},
          "right": {...}
        }
      ]
    }
  ]
}
```

---

## Migration from Flat to Expression Tree

If you have existing flat CTT structures:

**Before (Flat):**
```python
{
  "task_id": "parent",
  "operator": "sequence",
  "children": [task1, task2, task3]
}
```

**After (Expression Tree):**
```python
{
  "task_id": "parent",
  "children_tree": [
    {
      "operator": "sequence",
      "left": task1,
      "right": {
        "operator": "sequence",
        "left": task2,
        "right": task3
      }
    }
  ]
}
```

---

## Validation

Both flat and expression tree structures are validated by `validate_ctt_tree()`:

```python
from support_lib.CTT import validate_ctt_tree

errors = validate_ctt_tree(root_tasks)
if errors:
    print("Validation errors:")
    for error in errors:
        print(f"  - {error}")
else:
    print("Valid CTT tree!")
```

---

## TypeScript/Python Type Definitions

### Python Types

```python
CttTask(TypedDict):
    task_id: str
    title: str
    task_description: str
    optional: bool = False
    iterative: bool = False
    children: List[CttTask] = []           # Old-style flat
    children_tree: List[CttTask | CttOperatorNode] = []  # New-style tree

CttOperatorNode(TypedDict):
    operator: Literal["sequence", "choice", "interleaving", "disabling"]
    left: Union[CttTask, CttOperatorNode]
    right: Union[CttTask, CttOperatorNode]
```

---

## Testing

See `tests/test_expression_tree_ctt.py` for comprehensive examples:

```bash
python tests/test_expression_tree_ctt.py
```

---

## References

- **W3C CTT Standard:** https://www.w3.org/TR/ttml1/
- **Concurrent Task Trees Research:** See `Lib/CTT/ConcurTaskTrees_Research.md`
- **LangGraph Documentation:** https://python.langchain.com/docs/concepts/langgraph/


