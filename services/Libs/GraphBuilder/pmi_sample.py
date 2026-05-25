import math
from collections import defaultdict

# 1. Your existing co-occurrence dictionary
# Format: {(word1, word2): co_occurrence_weight}
co_occurrences = {
    ('apple', 'pie'): 15.0,
    ('apple', 'juice'): 5.0,
    ('orange', 'juice'): 10.0,
    ('the', 'apple'): 50.0,  # 'the' is common, so its PMI should drop
}


def calculate_pmi_dictionary(co_occur_dict):
    # Step 2: Calculate total weights and marginal (individual) item weights
    total_pair_weight = sum(co_occur_dict.values())

    item_weights = defaultdict(float)
    for (item1, item2), weight in co_occur_dict.items():
        # Add the weight to both individual items
        item_weights[item1] += weight
        item_weights[item2] += weight

    # The total weight of all individual occurrences is exactly double
    # the total pair weight, because each pair contains two items.
    total_item_weight = total_pair_weight * 2

    # Step 3: Calculate PMI and PPMI
    pmi_dict = {}
    ppmi_dict = {}

    for (item1, item2), weight in co_occur_dict.items():
        # Calculate probabilities
        p_xy = weight / total_pair_weight
        p_x = item_weights[item1] / total_item_weight
        p_y = item_weights[item2] / total_item_weight

        # Calculate PMI
        # Adding a small epsilon (e.g., 1e-10) to the denominator prevents division by zero
        # though it shouldn't happen here if the item exists in the dict.
        pmi = math.log2(p_xy / (p_x * p_y))

        pmi_dict[(item1, item2)] = pmi
        ppmi_dict[(item1, item2)] = max(0, pmi)  # PPMI variant

    return pmi_dict, ppmi_dict


# Run the function
pmi_matrix, ppmi_matrix = calculate_pmi_dictionary(co_occurrences)

# View the results
for pair in co_occurrences.keys():
    print(f"Pair: {pair} | Raw: {co_occurrences[pair]} | PMI: {pmi_matrix[pair]:.3f} | PPMI: {ppmi_matrix[pair]:.3f}")