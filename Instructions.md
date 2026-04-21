-Install last stable versions of langgraph , langchain , fastmcp , textual(TUI, CLI package) to the environment (python 3.12)
-Install a language detector , lemmatizer(at the very least for English and Turkish)

-Create a folder "Evergreen" .
-Create a folder "TUI" . 
-Create a folder "Agents" .
-Create a folder "Agents/Tools" .
-Create a folder "Agents/Prompts" .
-Create a folder "Agents/Nodes" .

-Create a folder in "Agents/Nodes" - name it something, in it an Input.txt and a .py file , in it a langgraph node that is instructed with taking the text and processing it to most minimal graph connections , every node is a word and the same for relationships , process output to Output.txt in the same folder - if it's possible to do this without an LLM do it with that to reduce cost or add as an alternative .
-Create a folder - name it something, in it a .py file that takes Input.txt and lemmatizes the text in it and outputs the lemmatized version to Output.txt , not having a main , main is in the root as main.py fill if you will .

-For each Input.txt fill it with something and test the Output.txt to see if it's working as intended , if not fix the code and test again until it works as intended . If a LLM is necessary to test like graph nodes skip LLM necessary parts .
