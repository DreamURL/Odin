# LLMscript.py
from langchain.prompts import PromptTemplate
from langchain.agents import AgentExecutor, create_react_agent

from Ollama_model import get_ollama_llm
from Langchain.Searchtool import file_system_search


def create_agent_executor(default_path: str):
    print("에이전트를 생성합니다...")
    llm = get_ollama_llm()
    tools = [file_system_search]


    prompt_template = """Answer the following questions as best you can. You have access to the following tools:

{tools}

Use the following format:

Question: the input question you must answer
Thought: you should always think about what to do (in Korean)
Action: the action to take, should be one of [{tool_names}]
Action Input: {{"search_query": "keyword", "base_path": "{default_path}", "limit": 200, "reindex": false}}
Observation: the result of the action
... (this Thought/Action/Action Input/Observation can repeat N times)
Thought: I now know the final answer (in Korean)
Final Answer: the final answer to the original input question (in Korean)

Important: 
- Search by name/path only. Do NOT search file contents in this tool.
- If there are too many results, you can lower "limit" in Action Input.
- If you suspect the index is stale, set "reindex": true to rebuild the map.
- Action Input should be a JSON string like {{"search_query": "keyword", "base_path": "{default_path}", "limit": 200, "reindex": false}}
- The program asks the user for a base path at startup; use that as {default_path} in tool calls.
- Think and answer in Korean

Begin!

Question: {input}
Thought:{agent_scratchpad}"""

    prompt = PromptTemplate.from_template(prompt_template).partial(default_path=default_path)
    agent = create_react_agent(llm, tools, prompt)
    agent_executor = AgentExecutor(
        agent=agent,
        tools=tools,
        verbose=True,
        handle_parsing_errors=True,
        max_iterations=3,
        early_stopping_method="force"
    )
    
    print("에이전트 생성이 완료되었습니다.")
    return agent_executor