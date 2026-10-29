from langchain_mistralai import ChatMistralAI
from dotenv import load_dotenv
from .tools.assets import get_asset_tool, get_asset_stats_tool, get_employee_assets_tool, get_expiring_warranties_tool, get_unassigned_assets_tool,search_assets_tool
from .tools.announcements import get_announcement_tool, search_announcements_tool,get_active_announcements_tool,get_department_announcements_tool,get_employee_announcements_tool
from .tools.department import get_department_info_tool, get_departments_tool
from .tools.employees import get_employee_tool, search_employees_tool, get_employee_stats_tool
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
model=ChatMistralAI(model="open-mistral-7b",temperature=0)

RETRIEVAL_K = 8
DEBUG=True
MAX_DEBUG_CHARS=1500
trace=[]
def debug_print(node,**values):
    trace.append(node)
    if not DEBUG:
        return
    print(f"\n========== NODE: {node} ==========")
    for key,value in values.items():
        text=str(value)
        if len(text)>MAX_DEBUG_CHARS:
            text=text[:MAX_DEBUG_CHARS]+f"... [truncated, {len(text)} chars total]"
        print(f"{key}: {text}")
    print("="*50+"\n")

tools=[
       get_asset_tool, get_asset_stats_tool, get_employee_assets_tool, get_expiring_warranties_tool, get_unassigned_assets_tool,search_assets_tool,
       get_announcement_tool, search_announcements_tool,get_active_announcements_tool,get_department_announcements_tool,get_employee_announcements_tool,
       get_department_info_tool, get_departments_tool,
       get_employee_tool, search_employees_tool, get_employee_stats_tool,
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
    debug_print("Intent Classification: input",messages_in_state=len(state['messages']),conversation_history=query)
    prompt = f"""You are the intent classification component of an internal company assistant. Decide which information source is needed to answer the user's LATEST message, and extract the query for each source.

    Conversation history:
    {query}

    Classify the latest user message. Use earlier messages only to resolve references such as "it" or "that policy".

    The assistant has exactly two information sources.

    ============================================================
    SOURCE A: DATABASE (stored records about people, things and events, and counts or lists of them)
    ============================================================
    Tables and what each row stores:
    - employees: one row per employee: employee_id, first_name, last_name, gender, email, phone_number, address, date_of_birth, date_joined, job_title, department_id, manager_id (that employee's own manager), salary (that employee's own salary), employment_status.
    - departments: one row per department: department_id, name, description, budget, creation date. Each department also has counts of its employees, projects and announcements. This is the only place that holds information about a specific department.
    - leave_balances: one row per employee, leave type and year: total_days, used_days, remaining_days. Numbers only, no policy text.
    - leave_requests: one row per leave request: employee_id, leave_type (Annual, Sick, Casual, Unpaid, Maternity), start_date, end_date, reason, status (Pending, Approved, Rejected), approved_by.
    - assets: one row per company asset such as a laptop or phone: asset_tag, asset_type, brand, model, serial_number, purchase_date, purchase_cost, status, condition, warranty_expiry, assigned_to (an employee).
    - tickets: one row per support ticket: ticket_id, created_by, assigned_to, title, description, category, status, priority, due_at, resolved_at, closed_at.
    - ticket_comments: comments written on a ticket: ticket_id, author_id, comment, created_at.
    - projects: one row per project: name, description, department_id, project_manager_id, status (Planning, Active, On Hold, Completed), start_date, expected_end_date.
    - project_members: which employee works on which project, with role and joined_at.
    - announcements: company or department announcements: title, content, created_by, department_id, published_at, expires_at.

    The database holds ONLY these records. It never contains policies, rules, benefits, entitlements, procedures, company values, culture, or any explanation of how the company works. It also holds no company-level facts about money or ownership: no fundraising, valuation, share counts, stock option prices or equity terms, no salary bands, no benefit or contribution amounts. The only money values it stores are one employee's own salary, a department's budget and an asset's purchase cost. A question belongs to the database if its answer is stored in, or can be counted or listed from, these tables: a value for one particular record, OR a count, total, list or breakdown of records. Examples of such counts: how many employees the company has, how many employees are in a department or have a given status, how many tickets are open, which assets are unassigned.

    Named things are records. A named person, a named department (for example "Finance", "the Engineering department"), a project, an asset or a ticket is a specific record. When the user asks for "info", "details", "an overview", "a profile" or "to tell me about" such a named thing, or asks about its description, budget, headcount, projects or announcements, that is a database lookup. The user does not need to say "record" or "database".

    ============================================================
    SOURCE B: COMPANY HANDBOOK (documents)
    ============================================================
    The handbook explains how the company works in general. It covers:
    - Benefits and perks: health and disability insurance, vacation and sick leave, holidays, new parent leave, sabbatical, protected absences (for example bereavement or jury duty), learning and conference budgets, referral bonuses.
    - Compensation: salary bands and rubrics, equity and stock options, vesting, exercising options, fundraising and share counts.
    - Employment policies: at-will employment, working remotely, employee privacy, equal opportunity, complaints, drug and alcohol, code of conduct, the invention and confidentiality agreement.
    - How the team works: company values, mission, product principles, OKRs, one on ones, effective meetings, hack weeks, communication and Slack etiquette, sharing files, budgeting, who people report to in general, onboarding and the first day.
    - Hiring: the interview process, sourcing candidates, changes to the handbook.
    Any question about what the company allows, requires or offers, how much, how long, how often, when, who is responsible, or how something is normally done belongs to the handbook. This includes questions whose answer is a number (an amount, a limit, a number of days, a percentage), because those numbers describe company rules, not stored records.
    The handbook does NOT describe individual departments or teams, their budgets, headcount, projects or announcements.

    ============================================================
    HOW TO DECIDE
    ============================================================
    Ask yourself: must the answer be READ or COUNTED from the stored records (people, leave, assets, tickets, projects, announcements, departments)? Then it is the database. Or does it explain a rule, benefit, policy, amount offered, or how things are done? Then it is the handbook. Words like "the company" or "our company" do not decide this; what is being asked for decides it.

    1. Database_Query: when the answer must be read or counted from stored records. This covers a specific record (a named person, a named department, an employee id, a ticket, project or asset identifier or name, or the speaker themself through "my", "I" or "me") AND counts, totals, lists or breakdowns across many records. Counting or listing needs no identifier.
    2. RAG_Query: when the question is about rules, amounts, limits, timing, process, benefits, tools, values or culture. Mentioning employees, leave, salary, managers, projects, assets or departments does NOT make a question a database question.
       - What a particular named person earns is a database question. Salary bands, pay rubrics and how compensation works are handbook questions.
       - Who a particular named person reports to is a database question. How reporting lines work in the company in general is a handbook question.
       - A person's own leave balance is a database question. How leave works, accrues or is approved is a handbook question.
       - Pay for a role, a level or a group of people (for example what founders or senior staff earn) is a handbook question. Pay of one named person is a database question.
       - Facts about the company as a whole (money raised, valuation, number of shares, option price, equity terms, which benefits or matching contributions exist) are handbook questions, even though they mention money, shares or employees.
       - How many employees, tickets, assets or projects exist right now is a database question (counted from records). How many days, weeks or people a policy allows is a handbook question.
       - Information about a particular named department (what it does, its budget, size, projects, announcements) is a database question. How departments or teams work in general (for example how budgeting is done or how teams communicate) is a handbook question.
    3. Mixed:have both queries: only when the message contains TWO different needs, a general policy part AND a record part (specific or counted). A question with several sub-questions that are all about handbook topics is still RAG_Query, not Mixed.
    4. Unclear: only when you cannot tell what is being asked at all, or when a question about one specific record gives no identifier and no "my" or "I". Counting or listing questions are never Unclear. A general question about the company is never Unclear. A question naming a department, person, project, asset or ticket is never Unclear.
    5. Irrelevant: not related to the company at all (small talk, weather, general trivia, writing help).
    6. If you are torn between RAG_Query and Database_Query and the message does NOT name a specific record and is NOT asking to count or list stored records, choose RAG_Query. This rule never applies when a specific person, department, project, asset or ticket is named: that is Database_Query.
    7. If a general question might not be covered by the handbook, still choose RAG_Query. Retrieval will find out whether the answer exists. Never choose Unclear or Irrelevant just because you are unsure the handbook covers the topic.

    ============================================================
    EXAMPLES
    ============================================================
    - "Which public holidays does the company observe?" -> RAG_Query
    - "What does the drug and alcohol policy say?" -> RAG_Query
    - "Does the company give employees a day off on their birthday?" -> RAG_Query (it may not be covered; retrieval decides)
    - "What are the steps for filing a complaint, who handles it, and is retaliation allowed?" -> RAG_Query (several sub-questions, all handbook)
    - "Does the company reimburse home internet costs?" -> RAG_Query
    - "How many people can be on a hack week team?" -> RAG_Query (a rule, not a count of records)
    - "How does budgeting work at the company?" -> RAG_Query (how things are done in general)
    - "What is Maria Lopez's job title?" -> Database_Query
    - "How many annual leave days do I have remaining?" -> Database_Query
    - "Who approved leave request 88?" -> Database_Query
    - "What is the status of ticket 105?" -> Database_Query
    - "How many employees does the company have?" -> Database_Query (count of employee records)
    - "How many tickets are still open?" -> Database_Query
    - "List all announcements." -> Database_Query
    - "Give me info about the Finance department." -> Database_Query (a named department is a specific record)
    - "What is the Engineering department's budget and how many people work there?" -> Database_Query
    - "Which departments have more than 10 employees?" -> Database_Query (a filtered list of records)
    - "What is the complaint procedure, and do I have any pending leave requests?" -> Mixed:have both queries
    - "What is the weather in Paris?" -> Irrelevant
    - "Can you look that up for me?" (nothing earlier in the conversation) -> Unclear

    ============================================================
    OUTPUT FIELDS
    ============================================================
    - intent: one of the allowed values.
    - reason: one short sentence explaining the choice.
    - rag_query: for RAG_Query and Mixed, a standalone search query for the handbook. Keep the user's own key terms and every detail they asked about, only resolve references from the conversation, and do not add words that were not asked. Keep all sub-questions of a multi-part question in one query. Otherwise null.
    - database_query: for Database_Query and Mixed, a standalone plain-language description of what to look up, count or list, including any identifier or name given. Keep it limited to what the user actually asked for and do not add details they did not request. Do not mention table or column names and do not start with the word retrieve. Otherwise null.
    """
    structured_model=model.with_structured_output(IntentClassification)
    answer=structured_model.invoke(prompt)
    
    
    print("\n========== INTENT DEBUG ==========")
    print("Intent:", answer["intent"])
    print("Reason:", answer["reason"])
    print("RAG query:", answer["rag_query"])
    print("Database query:", answer["database_query"])
    print("==================================\n")
    debug_print("Intent Classification: output",raw_answer=answer)
    return {
    'intent':answer,
    'Rag_query':answer['rag_query'],
    'Database_query':answer['database_query']}

def intent_router(state:StateAgent):
    intent=state['intent']['intent']
    if intent=='Database_Query':
        route="check_for_missing_info"
    elif intent=='RAG_Query':
        route="RAG_Query_Retrieval"
    elif intent== "Mixed:have both queries":
        route="not_implemented_yet"
    elif intent=="Unclear":
        route="ask_for_clarification"
    elif intent=="Irrelevant":
        route="handle_irrelevant_query"
    else:
        route="ask_for_clarification"
    debug_print("intent_router (router)",intent=intent,next_node=route)
    return route
    
def RAG_Query_Retrieval(state: StateAgent):
    query = state["Rag_query"]
    debug_print("RAG_Query_Retrieval: start",rag_query=query,k=RETRIEVAL_K,intent=state.get('intent'))

    chunks = vector_store.similarity_search(query, k=RETRIEVAL_K)

    print(f"\nQuery: {query}")
    print(f"Retrieved {len(chunks)} chunks")

    for i, chunk in enumerate(chunks, start=1):
        print(f"\n--- Chunk {i} ---")
        print(chunk.page_content)
        print("Metadata:", chunk.metadata)
    debug_print("RAG_Query_Retrieval: done",chunks_retrieved=len(chunks),sources=[chunk.metadata.get('source') or chunk.metadata.get('file_path') for chunk in chunks])
    return {"Retrieved_chunks": chunks}

#if unclear, then this, will add an edge between this and the get_query node
def ask_for_clarification(state:StateAgent):
    debug_print("ask_for_clarification",intent=state.get('intent'),selected_tool=state.get('selected_tool'),last_user_message=state['messages'][-1].content)
    return {'messages':[AIMessage(content="I am so sorry, i could not understand your previous request. Could you please make your query a bit more clear?")]}

#need to ask for the missing info
def ask_for_missing_info(state:StateAgent):
    debug_print("ask_for_missing_info",selected_tool=state.get('selected_tool'),tool_arguments=state.get('tool_arguments'),missing_arguments=state.get('missing_arguments'))
    return {'messages':[AIMessage(content=f"I am so sorry, I could not process your database query because it is missing these mandatory arguments: {state['missing_arguments']}. Please submit your complete query again, including these required arguments.")]}

class Infocheck(TypedDict):
    selected_tool:str|None
    reason:str
    available_arguments:dict


#if database query then this node will run
def check_for_missing_info(state:StateAgent):
    debug_print("check_for_missing_info: start",database_query=state['Database_query'],tools_available=len(tools))
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
    debug_print("check_for_missing_info: model tool selection",raw_answer=answer)
    selected_tool = next((tool for tool in tools if tool.name == answer["selected_tool"]), None)

    if selected_tool is None:
        debug_print("check_for_missing_info: no matching tool",requested_tool=answer["selected_tool"],known_tools=list(tools_by_names))
        return {'enough_info':False,'missing_arguments':[],'selected_tool':None,'tool_arguments':{}}

    available_arguments = answer["available_arguments"] or {}
    argument_schema = selected_tool.get_input_schema().model_json_schema()
    required_arguments = argument_schema.get("required", [])
    missing_arguments = [
        argument for argument in required_arguments
        if argument not in available_arguments
    ]
    debug_print("check_for_missing_info: argument check",selected_tool=selected_tool.name,tool_description=selected_tool.description,all_parameters=list(argument_schema.get("properties",{})),required_arguments=required_arguments,arguments_from_model=available_arguments,missing_arguments=missing_arguments,enough_info=len(missing_arguments)==0)

    if len(missing_arguments)==0:
        return {'enough_info':True,'missing_arguments':[],'selected_tool':selected_tool.name,'tool_arguments':available_arguments}
    else:
        return {'enough_info':False,'missing_arguments':missing_arguments,'selected_tool':selected_tool.name,'tool_arguments':available_arguments}

#is enough confitional edge for routing
def is_info_enough(state:StateAgent):
    if state["selected_tool"] is None:
        route="ask_for_clarification"
    elif state["enough_info"]:
        route="execute_tool"
    else:
        route="ask_for_missing_info"
    debug_print("is_info_enough (router)",selected_tool=state["selected_tool"],enough_info=state["enough_info"],missing_arguments=state["missing_arguments"],next_node=route)
    return route

#this after the execute_tool
def execute_tool(state:StateAgent):
    tool = tools_by_names[state["selected_tool"]]
    debug_print("execute_tool: calling",tool=tool.name,arguments=state["tool_arguments"])
    try:
        observation = tool.invoke(state["tool_arguments"])
        debug_print("execute_tool: success",result_type=type(observation).__name__,result=observation)
    except Exception as exc:
        observation = f"The database lookup failed: {exc}"
        debug_print("execute_tool: FAILED",error_type=type(exc).__name__,error=exc)
    return {"Database_result": observation}
    
def final_answer(state:StateAgent):
    question=next((message.content for message in reversed(state['messages']) if isinstance(message, HumanMessage)), "")
    selected=state.get('selected_tool')
    purpose=tools_by_names[selected].description.strip().split("\n\n")[0] if selected else ""
    lookup_note=f"The database results were produced by running the tool {selected} with these arguments: {state.get('tool_arguments')}. Tool purpose: {purpose}" if selected else "No database lookup was performed."
    debug_print("final_answer: input",question=question,lookup_note=lookup_note,standalone_request=state.get('Database_query'),database_result=state.get('Database_result'),chunks_in_prompt=len(state.get('Retrieved_chunks') or []),chunk_sources=[chunk.metadata.get('source') or chunk.metadata.get('file_path') for chunk in state.get('Retrieved_chunks') or []])
    prompt=f"""
    You are a helpful AI assistant for a company.

    Your task is to answer the user's question using the information
    provided in the database results and retrieved document chunks.

    User's latest question:
    {question}

    Database results:
    {state.get('Database_result')}

    How the database results were produced:
    {lookup_note}

    Retrieved document chunks:
    {state.get('Retrieved_chunks')}

    Instructions:
    1. Use the database results for company records and structured information.
       They are the exact output of the tool described above, run with the arguments shown, so every filter in those arguments (for example gender, employee id or department) has already been applied. Treat the results as correct and answer from them directly. Do not require the filter to appear as a column or field in the rows. A count, total or list returned by the tool is the answer to the matching question.
    2. Use the retrieved document chunks for company policies, procedures,
       and other documented information.
    3. If both sources contain relevant information, combine them into one
       clear and coherent answer.
    4. Do not invent facts. Only state numbers, names and details that appear in the database results or the retrieved chunks. Conclusions that follow directly from the tool arguments and the tool purpose are allowed, for example a count returned for gender male is the number of male employees.
    5. If the database result says the lookup failed or is empty, say so plainly. Only say information is missing if neither the results, the chunks nor the tool arguments answer the question.
    6. Present the answer in a clear, concise, and readable format.
    """

    response=model.invoke(prompt)
    debug_print("final_answer: output",answer=response.content,usage=getattr(response,'usage_metadata',None))

    return {"messages":[AIMessage(content=response.content)]}


def not_implemented_yet(state:StateAgent):
    debug_print("not_implemented_yet",intent=state.get('intent'),rag_query=state.get('Rag_query'),database_query=state.get('Database_query'))
    return {'messages':[AIMessage(content="This query type is not implemented yet. The database-query flow is currently available; document retrieval and mixed queries will be added later.")]}

def handle_irrelevant_query(state:StateAgent):
    debug_print("handle_irrelevant_query",intent=state.get('intent'),last_user_message=state['messages'][-1].content)
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
if __name__ == "__main__":
    messages = []
    while True:
        query = input("You: ")

        if query.lower() in ["exit", "quit"]:
            break

        messages.append(HumanMessage(content=query))

        trace.clear()
        result = app.invoke({"messages": messages})
        debug_print("turn summary",nodes_visited=" -> ".join(trace),intent=(result.get("intent") or {}).get("intent"),selected_tool=result.get("selected_tool"),tool_arguments=result.get("tool_arguments"),chunks_retrieved=len(result.get("Retrieved_chunks") or []),total_messages=len(result["messages"]))

        messages = result["messages"]

        print("Assistant:", messages[-1].content)