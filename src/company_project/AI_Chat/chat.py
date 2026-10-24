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

    The company assistant answers questions about company records, operations, policies, and internal documents.

    Classify the message into exactly one of these categories:

    1. Database_Query
    Use this when the question can be answered using structured company database records.
    The database contains these tables: announcements, assets, departments, employees, leave_balances, leave_requests, project_members, projects, ticket_comments, and tickets.
    Examples include checking an employee's department, finding a ticket's status, checking leave balances, looking up assigned assets, and retrieving project details.

    2. RAG_Query
    Use this when the question requires retrieving and understanding information from company documents, policies, guidelines, procedures, or other written material.
    Examples include asking about leave policies, expense reimbursement rules, or company procedures.

    3. Mixed:have both queries
    Use this when the message requires BOTH database records and document retrieval to answer fully.
    Extract the database-related part into database_query and the document-related part into rag_query.
    Each extracted query must be understandable on its own and preserve the information needed to answer that part of the user's request.

    4. Unclear
    Use this when the message appears related to the company but lacks enough information to determine what the user wants, or when essential details are ambiguous.
    Do not invent missing details. Extract a query only if a meaningful, sufficiently clear subquery can be identified.

    5. Irrelevant
    Use this when the message is unrelated to the company's information, records, documents, or operations, and is outside the assistant's intended scope.

    Extraction rules:
    - For Database_Query, populate database_query with the user's database-related question and set rag_query to None.
    - For RAG_Query, populate rag_query with the user's document-related question and set database_query to None.
    - For Mixed:have both queries, populate BOTH fields with their respective questions.
    - For Unclear, populate a field only if a meaningful subquery can be extracted; otherwise set it to None.
    - For Irrelevant, set both query fields to None.
    - Preserve relevant names, IDs, dates, departments, and other constraints from the original message.
    - Do not invent facts, identifiers, or additional requirements.
    - The reason field must briefly explain the classification.
    - Classify based on the information sources required, not merely on keywords appearing in the message.
    Use the conversation history to understand the user's latest message.
    Classify the latest user message in the context of previous messages.
    If the latest message is a follow-up, combine its meaning with the relevant
    previous messages to extract a complete, understandable query.
    Do not treat previous user requests as new requests unless the latest
    message refers to them.
    """
    structured_model=model.with_structured_output(IntentClassification)
    answer=structured_model.invoke(prompt)
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

def RAG_Query_Retrieval(state:StateAgent):
    chunks = vector_store.similarity_search(
    state['Rag_query'],
    k=3)
    return {"Retrieved_chunks":chunks}

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


graph=StateGraph(StateAgent)

graph.add_node("Intent Classification", intent_classification)
graph.add_node("Get_query_from_user",get_the_query)
graph.add_node("ask_for_missing_info",ask_for_missing_info)
graph.add_node("ask_for_clarification",ask_for_clarification)
graph.add_node("check_for_missing_info",check_for_missing_info)
graph.add_node("execute_tool",execute_tool)
graph.add_node("final_answer",final_answer)
graph.add_node("not_implemented_yet",not_implemented_yet)
graph.add_node("handle_irrelevant_query",handle_irrelevant_query)
graph.add_node("RAG_Query_Retrieval",RAG_Query_Retrieval)

graph.add_edge(START,"Get_query_from_user")
graph.add_edge("Get_query_from_user","Intent Classification")
graph.add_conditional_edges("Intent Classification",intent_router)
graph.add_conditional_edges("check_for_missing_info",is_info_enough)
graph.add_edge("ask_for_missing_info","Get_query_from_user")
graph.add_edge("ask_for_clarification","Get_query_from_user")
graph.add_edge("execute_tool","final_answer")
graph.add_edge("RAG_Query_Retrieval","final_answer")
graph.add_edge("final_answer",END)
graph.add_edge("not_implemented_yet",END)
graph.add_edge("handle_irrelevant_query",END)

app=graph.compile()
result=app.invoke({"messages": []})
print(result["messages"][-1].content)