# SYSTEM_PROMPT REFACTORED: From Role-Play to Educational

## The Problem with "You are an expert"

### ❌ BAD PRACTICE (Previous)
```python
"You are a ConcurTaskTrees (CTT) expert. Parse task descriptions and output..."
```

**Issues:**
- Role-playing without knowledge doesn't teach the LLM
- LLM might hallucinate "expert" knowledge incorrectly
- Lacks concrete examples and theory
- Relies on LLM guessing what CTT is
- Vague and unmeasurable expectations

### ✅ GOOD PRACTICE (Now)
```python
"CONCURRENT TASK TREES (CTT) - REFERENCE GUIDE
CTT is a formal model for representing complex workflows...
[detailed theory, examples, rules, etc.]"
```

**Benefits:**
- Teaches CTT fundamentals, not role-playing
- Provides concrete theory and rationale
- Includes real-world examples
- Clear validation rules with reasoning
- LLM applies knowledge, not guesses

---

## What Changed

### NEW SYSTEM_PROMPT STRUCTURE

1. **Title & Definition** (What is CTT?)
   - Explains CTT as a formal model
   - States its purpose and value

2. **Core Concepts** (Why does it exist?)
   - Task hierarchy
   - Metadata and properties
   - Operator semantics

3. **Task Structure** (What does it look like?)
   - LEAF TASK example (0-1 children)
   - BRANCH TASK example (2+ children)
   - Shows actual JSON structure

4. **Operators - Execution Semantics** (How do they work?)
   - SEQUENCE: "Execute ALL children in STRICT ORDER"
   - CHOICE: "Execute EXACTLY ONE of the children"
   - INTERLEAVING: "Execute ALL children SIMULTANEOUSLY"
   - DISABLING: "A task CAN INTERRUPT and override"
   - Each with: meaning, use case, example

5. **Validation Rules** (What are the constraints?)
   - RULE 1: Operator Placement (only 2+ children)
   - RULE 2: Default Behavior (sequence is default)
   - RULE 3: Iteration vs Operator (iterative flag, not operator='*')
   - RULE 4: Optional & Iterative (independent flags)

6. **Status Values** (What states exist?)
   - Defined: pending, running, blocked, done, failed
   - Clear meaning for each

7. **Practical Examples** (How to apply?)
   - EXAMPLE 1: Web Scraper (sequential + iterative)
   - EXAMPLE 2: Test Framework (mixed operators, complex)
   - Shows real JSON structures

8. **Validation Checklist** (How to verify?)
   - 8-point checklist to verify CTT correctness

9. **Output Format** (What should be returned?)
   - Exact JSON structure expected
   - Specific formatting rules

---

## Comparison: Old vs New

| Aspect | Old (Role-play) | New (Educational) |
|--------|-----------------|-------------------|
| **Approach** | "You are an expert" | "Here's what CTT is..." |
| **Theory** | Missing | Included |
| **Examples** | None | 2 detailed examples |
| **Operator Explanations** | One-liners | Detailed semantics |
| **Validation** | Implicit | Explicit 8-point checklist |
| **Use Cases** | Not stated | Clear for each operator |
| **Structure** | Cryptic | Well-organized sections |
| **Length** | ~150 words | ~800 words (comprehensive) |
| **LLM Confidence** | Low (guessing) | High (informed) |

---

## Key Improvements

### BEFORE: Operator Definition
```
"sequence (>>, enabling, sequential, pipeline): execute tasks one-by-one in order"
```

### AFTER: Operator Explanation
```
"1. SEQUENCE (>>, enabling, sequential, pipeline)
   - Execute ALL children in STRICT ORDER, one after another
   - Child N cannot start until Child N-1 completes
   - Use when: tasks have dependencies or order matters
   - Example: Fetch Data → Process → Save (must happen in order)
   - Default when 2+ children and no operator specified"
```

---

## Real Examples in Prompt

### Example 1: Web Scraper (Shows Sequential + Iterative)
```json
{
  "task_id": "parse",
  "title": "Parse Products",
  "iterative": true,
  "children": [
    { "task_id": "name", "title": "Extract Name" },
    { "task_id": "price", "title": "Extract Price" },
    { "task_id": "desc", "title": "Extract Description" }
  ],
  "operator": "sequence"
}
```
**Teaching Point:** How to combine iterative flag with sequential operator

### Example 2: Test Framework (Shows Mixed Operators)
```json
{
  "task_id": "test",
  "title": "Run Tests",
  "operator": "sequence",
  "children": [
    {
      "task_id": "suite",
      "title": "Execute Test Suites",
      "operator": "interleaving",
      "children": [
        { "task_id": "unit", "title": "Unit Tests", "iterative": true },
        { "task_id": "integration", "title": "Integration Tests" },
        { "task_id": "perf", "title": "Performance Tests" }
      ]
    },
    {
      "task_id": "handle",
      "title": "Handle Results",
      "operator": "choice",
      "children": [
        { "task_id": "pass", "title": "All Passed" },
        { "task_id": "retry", "title": "Auto-Retry" },
        { "task_id": "report", "title": "Generate Report" }
      ]
    }
  ]
}
```
**Teaching Point:** How to nest different operators (sequence > interleaving > choice)

---

## Impact on LLM Output Quality

### With Educational Prompt:
✅ LLM understands CTT theory  
✅ LLM knows when to use each operator  
✅ LLM validates its own output  
✅ LLM applies rules consistently  
✅ LLM produces correct JSON first attempt  

### Without Educational Prompt:
❌ LLM guesses what "expert" means  
❌ LLM might confuse operators  
❌ LLM forgets validation rules  
❌ LLM produces invalid JSON  
❌ Requires multiple retries/corrections  

---

## Philosophy

This approach follows best practices in prompt engineering:

**Teach, don't role-play:**
- Instead of "act like an expert"
- Say "here's the knowledge you need"

**Show, don't tell:**
- Instead of just rules
- Provide concrete examples

**Explicit, don't implicit:**
- Instead of hoping LLM guesses
- State expectations clearly

---

## Result

The new SYSTEM_PROMPT:
- **Educates** the LLM about CTT
- **Provides** theory and examples
- **Guides** through explicit rules
- **Validates** with checklists
- **Empowers** LLM to produce correct output

This is production-ready, scalable, and maintainable! 🚀

