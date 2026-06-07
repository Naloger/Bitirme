class -> TextNormalizer
functions ->
main function
- normalize_text(text: str) -> list[str] -> list of keywords -> count of times they appear in the input

helper functions
- lemmatize : to normalize to basic standarts, maybe use a general lemmatizer
- clean_up_forbidden : clean up the forbidden words from the text, maybe use a predefined list of forbidden words
- create_cooccurance_matrix : create a matrix of co-occurance of the keywords in the text,
maybe use a dictionary to store the count of co-occurance
maybe use sliding window or other techniques

PPMI helper functions
- calculate_ppmi : to calculate the PPMI values for the co-occurance matrix, maybe use the formula for PPMI
- filter_keywords : to filter the keywords based on their PPMI values, maybe use a threshold to filter out the keywords with low PPMI values

Database helper functions
- save_to_database : to save the keywords and their counts to the database, maybe use a simple database like SQLite or a more complex one like MongoDB
- retrieve_from_database : to retrieve the keywords and their counts from the database, maybe use a simple query to retrieve the data based on certain criteria
- update_database : to update the keywords and their counts in the database, maybe use a simple query to update the data based on certain criteria
- generate_as_matrix : to generate a matrix of keywords and their counts for further analysis, maybe use a simple matrix representation like a 2D list or a more complex one like a sparse matrix
- ppmi_post_process_matrix : to post process the PPMI matrix
