from langchain_mistralai import ChatMistralAI
from dotenv import load_dotenv
from .tools.assets import get_asset_tool, get_asset_stats_tool, get_employee_assets_tool, get_expiring_warranties_tool, get_unassigned_assets_tool,search_assets_tool
from .tools.announcements import get_announcement_tool, search_announcements_tool,get_active_announcements_tool,get_department_announcements_tool,get_employee_announcements_tool
from .tools.department import get_department_info_tool, get_departments_tool
from .tools.employees import get_employee_tool, search_employees_tool
from .tools.leave_balances import get_leave_balance_tool, search_leave_balances_tool
from .tools.leave_requests import get_current_leaves_tool,get_leave_request_tool,search_leave_requests_tool
from .tools.project_members import get_employee_project_memberships_tool,get_project_member_tool,get_project_members_tool,search_project_members_tool
from .tools.projects import get_employee_projects_tool,get_project_tool,get_project_stats_tool,search_projects_tool
from .tools.ticket_comments import get_comment_tool,get_comment_count_tool,get_latest_ticket_comment_tool,get_ticket_comments_tool,search_ticket_comments_tool
from .tools.tickets import get_ticket_tool,get_ticket_stats_tool,get_unassigned_tickets_tool,search_tickets_tool
from langgraph.graph import StateGraph,MessagesState,START,END
from typing import TypedDict,List,Literal,Any
from langchain_core.messages import HumanMessage, AIMessage
from .Vector_db.vector_db import vector_store

load_dotenv()
model=ChatMistralAI(model="open-mistral-7b")

tools=[
       get_asset_tool, get_asset_stats_tool, get_employee_assets_tool, get_expiring_warranties_tool, get_unassigned_assets_tool,search_assets_tool,
       get_announcement_tool, search_announcements_tool,get_active_announcements_tool,get_department_announcements_tool,get_employee_announcements_tool,
       get_department_info_tool, get_departments_tool,
       get_employee_tool, search_employees_tool,
       get_leave_balance_tool, search_leave_balances_tool,
       get_current_leaves_tool,get_leave_request_tool,search_leave_requests_tool,
       get_employee_project_memberships_tool,get_project_member_tool,get_project_members_tool,search_project_members_tool,
       get_employee_projects_tool,get_project_tool,get_project_stats_tool,search_projects_tool,
       get_comment_tool,get_comment_count_tool,get_latest_ticket_comment_tool,get_ticket_comments_tool,search_ticket_comments_tool,
       get_ticket_tool,get_ticket_stats_tool,get_unassigned_tickets_tool,search_tickets_tool
    ]

tools_by_names={tool.name: tool for tool in tools}



class IntentClassification(TypedDict):
    intent:Literal["Database_Query","RAG_Query","Mixed:have both queries","Unclear","Irrelevant"]
    reason:str
    rag_query:str|None
    database_query:str|None

class StateAgent(MessagesState):
    employee_email:str|None=None
    Rag_query:str|None=None
    Retrieved_chunks:List[str]|None=None
    intent:IntentClassification|None=None
    Database_query:str|None=None
    Database_result:Any=None
    enough_info:bool|None=None
    missing_arguments:List[str]|None=None
    selected_tool:str|None=None
    tool_arguments:dict|None=None

#getting the query from human and saving in messages, will add an edge between this and intent classification
def get_the_query(state:StateAgent):
    query=str(input('Enter your query: '))
    return {'messages':[HumanMessage(content=query)]}

#intent
def intent_classification(state:StateAgent):
    query = "\n".join(
    f"{'User' if isinstance(i,HumanMessage) else 'Assistant'}: {i.content}"
    for i in state['messages'])

    prompt = f"""You are an intent classification component for an internal company assistant. Your task is to classify the user's message and extract the relevant query or queries for the appropriate information source.

    Conversation history:
    {query}

    The company assistant answers questions using two distinct information sources: structured database records and company documents. You must understand the difference between them before classifying a query.

    **1. Database scope: Specific, structured records**

    The database stores concrete information about specific company entities and events. It does NOT serve as the source of general company policies, rules, or guidelines.

    The database contains the following tables:

    - **employees:** Specific employee information, such as first name, last name, email, phone number, job title, employment status, department, manager, and joining date.
    - **departments:** Specific department records and their stored details.
    - **leave_balances:** Individual employees' recorded leave balances, such as their available or remaining leave, depending on the fields stored in the table.
    - **leave_requests:** Specific leave requests submitted by employees, including their recorded dates, status, and other stored request details.
    - **assets:** Specific company assets, their assigned employees, and their recorded details.
    - **tickets:** Specific support tickets, including their recorded status, priority, category, creator, assignee, and other stored fields.
    - **ticket_comments:** Comments recorded on specific tickets.
    - **projects:** Specific company projects and their stored details.
    - **project_members:** Records identifying which employees are associated with which projects.
    - **announcements:** Specific announcements that have been recorded in the database, including their stored content and associated details.
    - **Other tables:** Use the actual fields and relationships in the database schema to determine what information they contain. Do not assume a table stores information that is not represented by its fields.

    Examples of database questions:
    - What is Sarah's email address?
    - Which department does employee 42 belong to?
    - How many vacation days does employee 42 have remaining?
    - Who is assigned to ticket 105?
    - What is the status of my leave request?
    - Which employees are assigned to project X?

    These questions concern actual records, individual values, or events stored in the database.

    **2. RAG scope: General knowledge, company policies, and guidelines**

    Company documents are the source of general company rules, policies, procedures, benefits, eligibility requirements, guidelines, and explanations of what employees are allowed, required, or entitled to do.

    This information is NOT necessarily stored in the database, even when it concerns employees, leave, assets, departments, or other entities that have database tables.

    Examples of document-based questions:
    - How many paid vacation days does the company offer employees?
    - Does the company provide paid vacation leave?
    - What is the company's vacation and sick leave policy?
    - Can an employee resign at any time?
    - How much notice must an employee give before resigning?
    - What are the rules for terminating employment?
    - What healthcare benefits does the company provide?
    - What is the procedure for requesting leave?
    - What are the guidelines for using company assets?

    These questions ask about general company policies or rules, not an individual employee's recorded information. Route them to RAG even if the question mentions employees, leave, resignation, termination, departments, or assets.

    **3. Important distinction: General rules versus actual records**

    Always identify what the user wants to know, not just the entities or keywords mentioned.

    For leave-related questions:
    - "How many paid vacation days does the company offer?" → RAG_Query. This asks about the company's general entitlement policy.
    - "How many vacation days do I have remaining?" → Database_Query. This asks about the current employee's individual balance.
    - "How many paid vacation days has employee 42 used?" → Database_Query only if the database stores sufficient information to answer this; otherwise, do not assume the required data exists.
    - "What is the vacation policy, and how many days do I have remaining?" → Mixed:have both queries. The policy comes from documents, and the individual balance comes from the database.

    For employment-related questions:
    - "Can I resign at any time?" → RAG_Query. This asks about company rules and resignation policy.
    - "What is my employment status?" → Database_Query. This asks for a specific employee record.
    - "What is the resignation policy, and what is my current employment status?" → Mixed:have both queries.

    For assets:
    - "What is the company's policy for using laptops?" → RAG_Query.
    - "Which laptop is assigned to employee 42?" → Database_Query.

    **4. Source selection rules**

    - Choose Database_Query when answering requires actual records or specific values stored in database tables.
    - Choose RAG_Query when answering requires company policies, general entitlements, rules, procedures, guidelines, or other document-based information.
    - Choose Mixed:have both queries only when the user's request genuinely requires both a database lookup and document retrieval.
    - Do not choose Database_Query just because a question mentions employees, leave, departments, assets, or another database entity.
    - Do not assume the database contains a policy simply because it contains records about the people or entities governed by that policy.
    - Do not invent database fields, records, or policy details.
    - If the user asks a general policy question, use RAG even if the policy is not currently known to exist in the available documents. Retrieval can determine whether supporting information is available.
    - If the question asks for a specific record but lacks a necessary identifier, classify it as Unclear only when that missing information prevents a meaningful query.
    - If the user asks about a policy and an individual record in the same request, classify it as Mixed and extract each part separately.
    """
    structured_model=model.with_structured_output(IntentClassification)
    answer=structured_model.invoke(prompt)
    
    
    print("\n========== INTENT DEBUG ==========")
    print("Intent:", answer["intent"])
    print("Reason:", answer["reason"])
    print("RAG query:", answer["rag_query"])
    print("Database query:", answer["database_query"])
    print("==================================\n")

    return {
    'intent':answer,
    'Rag_query':answer['rag_query'],
    'Database_query':answer['database_query']}

def intent_router(state:StateAgent):
    if state['intent']['intent']=='Database_Query':
        return "check_for_missing_info"
    elif state['intent']['intent']=='RAG_Query':
        return "RAG_Query_Retrieval"
    elif state['intent']['intent']== "Mixed:have both queries":
        return "not_implemented_yet"
    elif state['intent']['intent']=="Unclear":
        return "ask_for_clarification"
    elif state['intent']['intent']=="Irrelevant":
        return "handle_irrelevant_query"
    else:
        return "ask_for_clarification"
    
def RAG_Query_Retrieval(state: StateAgent):
    query = state["Rag_query"]

    chunks = vector_store.similarity_search(query, k=3)

    print(f"\nQuery: {query}")
    print(f"Retrieved {len(chunks)} chunks")

    for i, chunk in enumerate(chunks, start=1):
        print(f"\n--- Chunk {i} ---")
        print(chunk.page_content)
        print("Metadata:", chunk.metadata)

    return {"Retrieved_chunks": chunks}

#if unclear, then this, will add an edge between this and the get_query node
def ask_for_clarification(state:StateAgent):
    return {'messages':[AIMessage(content="I am so sorry, i could not understand your previous request. Could you please make your query a bit more clear?")]}

#need to ask for the missing info
def ask_for_missing_info(state:StateAgent):
    return {'messages':[AIMessage(content=f"I am so sorry, I could not process your database query because it is missing these mandatory arguments: {state['missing_arguments']}. Please submit your complete query again, including these required arguments.")]}

class Infocheck(TypedDict):
    selected_tool:str|None
    reason:str
    available_arguments:dict


#if database query then this node will run
def check_for_missing_info(state:StateAgent):
    tool_details = [
        {
            "name": tool.name,
            "description": tool.description,
            "args": tool.args
        }
        for tool in tools
    ]

    prompt=f"""Given these tools and their descriptions and argument schemas:
    {tool_details}

    Analyze the user's database query and select the single best tool to answer it, based on the tool's purpose, not just the arguments available.

    Database query:
    {state['Database_query']}

    Determine which arguments the user has actually provided in the query.
    Do not invent argument values.
    If the query does not provide a required argument, leave it out of available_arguments.
    If the argument can be obtained from trusted application context, do not assume it is available unless that context is provided.
    Do not execute the tool.

    Return:
    - selected_tool: the exact name of the best matching tool, or None if no suitable tool exists.
    - reason: briefly explain why this tool best matches the query.
    - available_arguments: a dictionary of argument names and their values that are explicitly supported by the query.
    """
    structured_model=model.with_structured_output(Infocheck)
    answer=structured_model.invoke(prompt)

    selected_tool = next((tool for tool in tools if tool.name == answer["selected_tool"]), None)

    if selected_tool is None:
        return {'enough_info':False,'missing_arguments':[],'selected_tool':None,'tool_arguments':{}}

    available_arguments = answer["available_arguments"] or {}
    argument_schema = selected_tool.get_input_schema().model_json_schema()
    required_arguments = argument_schema.get("required", [])
    missing_arguments = [
        argument for argument in required_arguments
        if argument not in available_arguments
    ]

    if len(missing_arguments)==0:
        return {'enough_info':True,'missing_arguments':[],'selected_tool':selected_tool.name,'tool_arguments':available_arguments}
    else:
        return {'enough_info':False,'missing_arguments':missing_arguments,'selected_tool':selected_tool.name,'tool_arguments':available_arguments}

#is enough confitional edge for routing
def is_info_enough(state:StateAgent):
    if state["selected_tool"] is None:
        return "ask_for_clarification"
    elif state["enough_info"]:
        return "execute_tool"
    else:
        return "ask_for_missing_info"

#this after the execute_tool
def execute_tool(state:StateAgent):
    tool = tools_by_names[state['selected_tool']]
    observation = tool.invoke(state["tool_arguments"])
    return {"Database_result": observation}
    
def final_answer(state:StateAgent):
    prompt=f"""
    You are a helpful AI assistant for a company.

    Your task is to answer the user's question using the information
    provided in the database results and retrieved document chunks.

    User's latest question:
    {state['Database_query'] or next((message.content for message in reversed(state['messages']) if isinstance(message, HumanMessage)), "")}

    Database results:
    {state.get('Database_result')}

    Retrieved document chunks:
    {state.get('Retrieved_chunks')}

    Instructions:
    1. Use the database results for company records and structured information.
    2. Use the retrieved document chunks for company policies, procedures,
       and other documented information.
    3. If both sources contain relevant information, combine them into one
       clear and coherent answer.
    4. Do not invent facts or make assumptions beyond the provided information.
    5. If the available information is insufficient to answer the question,
       clearly explain what information is missing.
    6. Present the answer in a clear, concise, and readable format.
    """

    response=model.invoke(prompt)

    return {"messages":[AIMessage(content=response.content)]}


def not_implemented_yet(state:StateAgent):
    return {'messages':[AIMessage(content="This query type is not implemented yet. The database-query flow is currently available; document retrieval and mixed queries will be added later.")]}

def handle_irrelevant_query(state:StateAgent):
    return {'messages':[AIMessage(content="I can help with company records, policies, documents, and operations. Please ask a question related to the company.")]}


graph = StateGraph(StateAgent)

graph.add_node("Intent Classification", intent_classification)
graph.add_node("ask_for_missing_info", ask_for_missing_info)
graph.add_node("ask_for_clarification", ask_for_clarification)
graph.add_node("check_for_missing_info", check_for_missing_info)
graph.add_node("execute_tool", execute_tool)
graph.add_node("final_answer", final_answer)
graph.add_node("not_implemented_yet", not_implemented_yet)
graph.add_node("handle_irrelevant_query", handle_irrelevant_query)
graph.add_node("RAG_Query_Retrieval", RAG_Query_Retrieval)

# Start directly with the query already provided in state
graph.add_edge(START, "Intent Classification")

graph.add_conditional_edges(
    "Intent Classification",
    intent_router
)

graph.add_conditional_edges(
    "check_for_missing_info",
    is_info_enough
)

graph.add_edge("execute_tool", "final_answer")
graph.add_edge("RAG_Query_Retrieval", "final_answer")

# These nodes return a response to the outer loop.
# The next user input is collected by the Python loop.
graph.add_edge("ask_for_clarification", END)
graph.add_edge("ask_for_missing_info", END)
graph.add_edge("not_implemented_yet", END)
graph.add_edge("handle_irrelevant_query", END)
graph.add_edge("final_answer", END)

app=graph.compile()
messages=[]
while True:
    query = input("You: ")

    if query.lower() in ["exit", "quit"]:
        break

    messages.append(HumanMessage(content=query))

    result = app.invoke({"messages": messages})

    messages = result["messages"]

    print("Assistant:", messages[-1].content)