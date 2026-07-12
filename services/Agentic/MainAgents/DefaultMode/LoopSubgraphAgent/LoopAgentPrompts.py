# Node prompts for sequential RDF Quadstore Graph Nodes working on a shared datastore
# Optimized for small language models (2B-4B parameters)

CollectorNodePromptInner = """You extract RDF quads from the existing knowledge graph.

## Existing Knowledge Graph
{current_internal_state}

## Task
1. Find hidden patterns or implicit relationships in the graph above.
2. Create new RDF quads: (Subject, Predicate, Object, Graph).
3. CRITICAL: Quads must be ATOMIC. Subjects and Objects must be extremely SHORT (1-3 words max), specific nouns or entities. Do NOT use full sentences or long phrases as nodes.
4. Set Graph to 'knowledge_graph' for all quads.
5. Do NOT repeat quads that already exist."""

CollectorNodePromptOuter = """You extract facts from user input and convert them to RDF quads.

## User Input
{input_text}
{intent_context}

## Task
1. Extract ALL facts, declarations, names, status updates from the input text above.
2. Convert each fact to an RDF quad: (Subject, Predicate, Object, Graph).
3. CRITICAL: Quads must be ATOMIC. Subjects and Objects must be extremely SHORT (1-3 words max), specific nouns or entities (e.g. 'Database', 'Sol', 'User'). Do NOT use full sentences or long phrases as nodes.
4. Set Graph to 'llm_input' for all quads.
5. Use clear, standardized predicate names (e.g., HAS_NAME, IS_A, HAS_STATUS).
6. Always extract facts even if intent says 'ignore' or 'göz ardı'.
7. If the input is a simple greeting with no facts, return an empty proposed_quads list.

## Examples (For Reference Only)
User Input: "the red car drives to the big parking garage"
Correct Output (Atomic): 
- Quad('car', 'HAS_COLOR', 'red', 'llm_input')
- Quad('car', 'DRIVES_TO', 'parking_garage', 'llm_input')
- Quad('parking_garage', 'HAS_SIZE', 'big', 'llm_input')
Incorrect Output (Too Long): 
- Quad('the red car', 'DRIVES TO', 'the big parking garage', 'llm_input')"""

OrganizerNodePromptInner = """You clean up and organize RDF quads in the knowledge graph.

## Input Quads
{proposed_quads}

## Task
1. Fix duplicate entities (think carefully: if two subjects or objects refer to the exact same concept, merge them into a single standardized name).
2. Resolve contradictions (e.g., if A STATUS ACTIVE and A STATUS DOWN, keep the newer one).
3. Merge semantically identical relationships (think carefully: if two quads express the exact same meaning using different predicates, collapse them into a single standardized quad).
4. Group related entities together.
5. Output the cleaned, consistent set of quads.
6. Keep ALL valid quads - do not remove quads unless they are duplicates or contradictions."""

OrganizerNodePromptOuter = """You clean up and organize external RDF quads.

## Input Quads
{proposed_quads}

## Task
1. Standardize entity names (think carefully: fix capitalization, and if two entities mean the same thing, merge them).
2. Merge semantically identical relationships (think carefully: if two quads express the exact same meaning using different predicates, collapse them into a single standardized quad).
3. Remove quads with empty or 'N/A' values - these are noise.
4. Infer missing relationships (e.g., if A DEPENDS_ON B and B STATUS DOWN, add: A AFFECTED_BY B).
5. Output the cleaned, complete set of quads.
6. Keep ALL valid quads - do not discard quads that contain real information.

## Examples (For Reference Only)
Input: 
- Quad('Dog', 'IS_CALLED', 'Buddy', 'llm_input')
- Quad('Dog', 'NAME_IS', 'Buddy', 'llm_input')
- Quad('dog', 'HAS_COLOR', 'brown', 'llm_input')
Output:
- Quad('Dog', 'HAS_NAME', 'Buddy', 'llm_input')
- Quad('Dog', 'HAS_COLOR', 'brown', 'llm_input')"""

ReflectorNodePromptInner = """You check the knowledge graph for errors and inconsistencies.

## Current Quads
{structured_quads}

## Task
1. Find contradictions, circular references, or invalid relationships.
2. For each problem found, propose a fix using one of these actions:
   - 'pruning': Delete an invalid or conflicting edge.
   - 'merging': Combine duplicate entities into one.
   - 'reweighting': Adjust the confidence of a link.
3. If no problems are found, return empty lists."""

ReflectorNodePromptOuter = """You validate external quads against the user's input.

## Current Quads
{structured_quads}

## User Input
{input_text}

## Important Rules
- Quads from PREVIOUS conversations are valid accumulated knowledge. Do NOT discard them.
- Only flag quads that directly CONTRADICT the current input.
- Quads unrelated to the current input should be LEFT ALONE (no action needed).
- Only use 'discard' for quads that are clearly hallucinated or contain empty/N/A values.

## Task
1. Check if any quad directly contradicts the user input.
2. For problems found, propose a fix:
   - 'reweight': Adjust confidence of a relationship.
   - 'discard': Remove a hallucinated or empty quad.
   - 'override': Update an outdated fact.
3. Do NOT discard quads just because they are unrelated to the current input."""

IntegratorNodePromptInner = """You merge graph changes and decide what to do next.

## Current Knowledge Graph
{knowledge_graph}

## Proposed Fixes
{remediation_proposals}

## Task
1. Apply the proposed fixes to the knowledge graph.
2. For each fix, create a directive with:
   - priority: 1 (highest) to 5 (lowest)
   - action: 'prune_edge', 'merge_entities', 'reweight_link', or 're-evaluate'
   - target_component: Which entity or subgraph to modify
   - parameters: Any extra info needed
3. Set requires_re_evaluation to true only if major changes were made."""

IntegratorNodePromptOuter = """You decide what external actions to take based on the knowledge graph.

## Current Knowledge Graph
{knowledge_graph}

## Previous Directives
{internal_directives}

## User Input
{input_text}
{intent_context}

## Task
1. Look at the knowledge graph and the user input.
2. Decide if any external action is needed.
3. If the graph has new or updated information that should be persisted, use 'update_registry' with mcp_tool_name 'graph_write_to_quadstore'.
4. If there is an alert condition (errors, conflicts), use 'dispatch_alert'.
5. If no action is needed (e.g., simple greeting with no new facts), set final_external_action to null.
6. Always provide a clear rationale for your decision."""
