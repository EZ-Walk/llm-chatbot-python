from llm import llm
from graph import graph
from langchain_core.prompts import ChatPromptTemplate, PromptTemplate
from langchain.schema import StrOutputParser
from langchain.tools import Tool
from tools import cypher
from utils import get_session_id
from tools.vector import get_movie_plot
from tools.cypher import cypher_qa

# Create a movie chat chain
chat_prompt = ChatPromptTemplate.from_messages(
    [
        ("system", "You are a movie expert providing information about movies."),
        ("human", "{input}"),
    ]
)

movie_chat = chat_prompt | llm | StrOutputParser()

# Create a set of tools
tools = [
    Tool.from_function(
        name="General Chat",
        description="For general movie chat not covered by other tools",
        func=movie_chat.invoke,
    ),
    Tool.from_function(
        name="Get Movie Plot",
        description="Get the plot of a movie",
        func=get_movie_plot,
    ),
    Tool.from_function(
        name="Movie information",
        description="Provide information about movie questions using cypher",
        func=cypher_qa
    )
]

# Create chat history callback
from langchain_neo4j import Neo4jChatMessageHistory

def get_memory(session_id):
    return Neo4jChatMessageHistory(
        session_id=session_id,
        graph=graph
    )
    
# Create the agent
from langchain.agents import AgentExecutor, create_react_agent
from langchain_core.runnables.history import RunnableWithMessageHistory
from langchain import hub

# modify the propmt 
# agent_prompt = hub.pull("hwchase17/react-chat")
agent_prompt = PromptTemplate.from_template("""
    You are a movie expert providing information about movies.
    Be as helpful as possible and return as much information as possible.
    Do not answer any questions using your pre-trained knowledge, only use the information provided in the context.

    Do not answer any questions that do not relate to movies, actors or directors.

    TOOLS:
    ------

    You have access to the following tools:

    {tools}

    To use a tool, please use the following format:

    ```
    Thought: Do I need to use a tool? Yes
    Action: the action to take, should be one of [{tool_names}]
    Action Input: the input to the action
    Observation: the result of the action
    ```

    When you have a response to say to the Human, or if you do not need to use a tool, you MUST use the format:

    ```
    Thought: Do I need to use a tool? No
    Final Answer: [your response here]
    ```

    Previous conversation history:
    {chat_history}

    New input: {input}
    {agent_scratchpad}
""")

agent = create_react_agent(llm, tools, agent_prompt)
agent_executor = AgentExecutor(
    agent=agent,
    tools=tools,
    verbose=True
)

chat_agent = RunnableWithMessageHistory(
    agent_executor,
    get_memory,
    input_messages_key="input",
    history_messages_key="chat_history",
)

# Create a handler to call the agent

def generate_response(user_input):
    # Create a handler that calls the agent
    
    response = chat_agent.invoke(
        {"input": user_input},
        {"configurable": {"session_id": get_session_id()}},
    )
    
    return response['output']

# modify the propmt 
agent_promtp = PromptTemplate.from_template("""
                                            You are a movie expert providing information about movies.
Be as helpful as possible and return as much information as possible.
Do not answer any questions using your pre-trained knowledge, only use the information provided in the context.

Do not answer any questions that do not relate to movies, actors or directors.

TOOLS:
------

You have access to the following tools:

{tools}

To use a tool, please use the following format:

```
Thought: Do I need to use a tool? Yes
Action: the action to take, should be one of [{tool_names}]
Action Input: the input to the action
Observation: the result of the action
```

When you have a response to say to the Human, or if you do not need to use a tool, you MUST use the format:

```
Thought: Do I need to use a tool? No
Final Answer: [your response here]
```

Previous conversation history:
{chat_history}

New input: {input}
{agent_scratchpad}
""")