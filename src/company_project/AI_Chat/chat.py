import os
from langchain_mistralai import ChatMistralAI
from dotenv import load_dotenv
from .tools.assets import get_asset_tool, get_asset_stats_tool, get_employee_assets_tool, get_expiring_warranties_tool, get_unassigned_assets_tool,search_assets_tool
from .tools.announcements import get_announcement_tool, search_announcements_tool,get_active_announcements_tool,get_department_announcements_tool,get_employee_announcements_tool
from .tools.department import get_department_info_tool, get_departments_tool
from .tools.employees import get_employee_tool, get_employee_by_email_tool, search_employees_tool, get_employee_stats_tool
from .tools.leave_balances import get_leave_balance_tool, search_leave_balances_tool
from .tools.leave_requests import get_employment_tool,get_leave_request_tool,search_leave_requests_tool
from .tools.project_members import get_employee_project_memberships_tool,get_project_member_tool,get_project_members_tool,search_project_members_tool
from .tools.projects import get_employee_projects_tool,get_project_tool,get_project_stats_tool,search_projects_tool
from .tools.ticket_comments import get_comment_tool,get_comment_count_tool,get_latest_ticket_comment_tool,get_ticket_comments_tool,search_ticket_comments_tool
from .tools.tickets import get_ticket_tool,get_ticket_stats_tool,get_employee_tickets_tool,search_tickets_tool
from langgraph.graph import StateGraph,MessagesState,START,END
from typing import TypedDict,List,Literal,Any
from langchain_core.messages import HumanMessage, AIMessage
from .Vector_db.vector_db import vector_store
import logging
from datetime import date
from ..auth.authorization import resolve_arguments, authorize, validate_policies
from sqlalchemy import select
from ..database.models import Employees, Department
from ..database.database import SessionLocal
from .resilience import call_with_retry, ServiceError, LLM_RETRY_KINDS, DB_RETRY_KINDS
from langchain_google_genai import ChatGoogleGenerativeAI
from .cache import lookup as cache_lookup, store as cache_store, purge_stale
load_dotenv()
model = ChatGoogleGenerativeAI(model="gemini-2.5-flash", temperature=0, timeout=30, max_retries=1)

load_dotenv()
# model=ChatMistralAI(model="open-mistral-7b",temperature=0,timeout=30,max_retries=1)
logger = logging.getLogger(__name__)

RETRIEVAL_K = 8
DEBUG = os.getenv("CHAT_DEBUG") == "1"
RECORD_TRACE = False
MAX_DEBUG_CHARS=1500
trace=[]
def debug_print(node,**values):
    if RECORD_TRACE:
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

def llm_failure(node, err: ServiceError):
    debug_print(f"{node}: FAILED", kind=err.kind, error=repr(err.original))
    return {"messages":[AIMessage(content=err.user_message)], "llm_error":err.user_message,
            "selected_tool":None, "tool_arguments":{}, "enough_info":False, "missing_arguments":[]}

tools=[
       get_asset_tool, get_asset_stats_tool, get_employee_assets_tool, get_expiring_warranties_tool, get_unassigned_assets_tool,search_assets_tool,
       get_announcement_tool, search_announcements_tool,get_active_announcements_tool,get_department_announcements_tool,get_employee_announcements_tool,
       get_department_info_tool, get_departments_tool,
       get_employee_tool, get_employee_by_email_tool, search_employees_tool, get_employee_stats_tool,
       get_leave_balance_tool, search_leave_balances_tool,
       get_employment_tool,get_leave_request_tool,search_leave_requests_tool,
       get_employee_project_memberships_tool,get_project_member_tool,get_project_members_tool,search_project_members_tool,
       get_employee_projects_tool,get_project_tool,get_project_stats_tool,search_projects_tool,
       get_comment_tool,get_comment_count_tool,get_latest_ticket_comment_tool,get_ticket_comments_tool,search_ticket_comments_tool,
       get_ticket_tool,get_ticket_stats_tool,get_employee_tickets_tool,search_tickets_tool
    ]

tools_by_names={tool.name: tool for tool in tools}
validate_policies(tools_by_names)



class IntentClassification(TypedDict):
    intent:Literal["Database_Query","RAG_Query","Mixed:have both queries","Unclear","Irrelevant"]
    reason:str
    rag_query:str|None
    database_query:str|None

class User(TypedDict):
    employee_id: int
    first_name: str
    last_name: str
    gender: str
    email: str
    phone_number: str
    date_joined: date
    job_title: str
    employment_status: str
    department_name: str
    manager_id: int | None
    role: str

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
    refers_to_self:bool|None=None
    denial_reason:str|None=None
    user: User
    llm_error:str|None=None
    retrieval_error:bool|None=None
    cache_hit: bool | None = None
    cache_score: float | None = None

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
    - departments: one row per department: department_id, name, description, creation date. Each department also has counts of its employees, projects and announcements. Department budget values are not available through the current database tools.
    - leave_balances: one row per employee, leave type and year: total_days, used_days, remaining_days. Numbers only, no policy text.
    - leave_requests: one row per leave request: employee_id, leave_type (Annual, Sick, Casual, Unpaid, Maternity), start_date, end_date, reason, status (Pending, Approved, Rejected), approved_by.
    For a specific employee's submitted leave requests, use get_employment_tool with only that employee's ID; it returns requests across all leave types and statuses.
    - assets: one row per company asset such as a laptop or phone: asset_tag, asset_type, brand, model, serial_number, purchase_date, purchase_cost, status, condition, warranty_expiry, assigned_to (an employee).
    - tickets: one row per support ticket: ticket_id, created_by, assigned_to, title, description, category, status, priority, due_at, resolved_at, closed_at.
    - ticket_comments: comments written on a ticket: ticket_id, author_id, comment, created_at.
    - projects: one row per project: name, description, department_id, project_manager_id, status (Planning, Active, On Hold, Completed), start_date, expected_end_date.
    - project_members: which employee works on which project, with role and joined_at.
    - announcements: company or department announcements: title, content, created_by, department_id, published_at, expires_at.

    The database holds ONLY these records. It never contains policies, rules, benefits, entitlements, procedures, company values, culture, or any explanation of how the company works. It also holds no company-level facts about money or ownership: no fundraising, valuation, share counts, stock option prices or equity terms, no salary bands, no benefit or contribution amounts. The money values available through database tools are one employee's own salary and an asset's purchase cost. Department budget values are not available through the current database tools. A question belongs to the database if its answer is available in, or can be counted or listed from, these tools: a value for one particular record, OR a count, total, list or breakdown of records. Examples of such counts: how many employees the company has, how many employees are in a department or have a given status, how many tickets are open, which assets are unassigned.

    Named things are records. A named person, a named department (for example "Finance", "the Engineering department"), a project, an asset or a ticket is a specific record. When the user asks for "info", "details", "an overview", "a profile" or "to tell me about" such a named thing, or asks about its description, headcount, projects or announcements, that is a database lookup. Do not claim or infer department budget values; the current database tools do not return them. The user does not need to say "record" or "database".

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
    The handbook does NOT describe individual departments or teams, their headcount, projects or announcements.

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
       - Information about a particular named department (what it does, its size, projects or announcements) is a database question. Department budget values are unavailable through the current database tools. How departments or teams work in general (for example how budgeting is done or how teams communicate) is a handbook question.
    3. Mixed:have both queries: only when the message contains TWO different needs, a general policy part AND a record part (specific or counted). A question with several sub-questions that are all about handbook topics is still RAG_Query, not Mixed.
    4. Unclear: only when you cannot tell what is being asked at all, or when a question about one specific record gives no identifier and no "my" or "I". Counting or listing questions are never Unclear. A general question about the company is never Unclear. A question naming a department, person, project, asset or ticket is never Unclear.
    5. Irrelevant: not related to the company at all (small talk, weather, general trivia, writing help).
    6. If you are torn between RAG_Query and Database_Query and the message does NOT name a specific record and is NOT asking to count or list stored records, choose RAG_Query. This rule never applies when a specific person, department, project, asset or ticket is named: that is Database_Query.
    7. If a general question might not be covered by the handbook, still choose RAG_Query. Retrieval will find out whether the answer exists. Never choose Unclear or Irrelevant just because you are unsure the handbook covers the topic.
    8. If the previous assistant message asked the user for missing details (such as an employee id, a ticket number, a name or an email), the latest message is the answer to that question. Combine it with the earlier request and classify the combined request, as if the user had said everything in one message. A short reply such as a number or a name is never Unclear in that situation.

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
    - "How many people work in the Engineering department?" -> Database_Query
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
    try:
        answer=call_with_retry(lambda: structured_model.invoke(prompt), step="intent classification",
                               retry_on=LLM_RETRY_KINDS,
                               validate=lambda a: isinstance(a,dict) and bool(a.get("intent")))
    except ServiceError as err:
        return llm_failure("Intent Classification", err)
    debug_print("Intent Classification: output",raw_answer=answer)
    return {
    'intent':answer,
    'Rag_query':answer.get('rag_query'),
    'Database_query':answer.get('database_query')}

def intent_router(state:StateAgent):
    if state.get("llm_error"):
        return END
    intent=state['intent']['intent']
    if intent=='Database_Query':
        route="check_for_missing_info"
    elif intent=='RAG_Query':
        route = "check_cache"  
    elif intent== "Mixed:have both queries":
        route=[node for node,part in (("check_for_missing_info",state['Database_query']),("RAG_Query_Retrieval",state['Rag_query'])) if part] or "ask_for_clarification"
    elif intent=="Unclear":
        route="ask_for_clarification"
    elif intent=="Irrelevant":
        route="handle_irrelevant_query"
    else:
        route="ask_for_clarification"
    debug_print("intent_router (router)",intent=intent,next_node=route)
    return route

# new node + router
def check_cache(state: StateAgent):
    query = state["Rag_query"]
    hit = cache_lookup(query)
    debug_print("check_cache", rag_query=query, hit=bool(hit),
                score=hit.score if hit else None,
                matched_query=hit.matched_query if hit else None)
    if hit:
        return {"cache_hit": True, "cache_score": hit.score,
                "messages": [AIMessage(content=hit.answer)]}
    return {"cache_hit": False}

def after_cache_check(state: StateAgent):
    return END if state.get("cache_hit") else "RAG_Query_Retrieval"
    
def RAG_Query_Retrieval(state: StateAgent):
    query = state["Rag_query"]
    debug_print("RAG_Query_Retrieval: start",rag_query=query,k=RETRIEVAL_K,intent=state.get('intent'))

    try:
        chunks = call_with_retry(lambda: vector_store.similarity_search(query, k=RETRIEVAL_K),
                                 step="document search", service="document search service")
    except ServiceError as err:
        debug_print("RAG_Query_Retrieval: FAILED", kind=err.kind, error=repr(err.original))
        return {"Retrieved_chunks": [], "retrieval_error": True}

    debug_print("RAG_Query_Retrieval: done",chunks_retrieved=len(chunks),sources=[chunk.metadata.get('source') or chunk.metadata.get('file_path') for chunk in chunks])
    return {"Retrieved_chunks": chunks}

#if unclear, then this, will add an edge between this and the get_query node
def ask_for_clarification(state:StateAgent):
    debug_print("ask_for_clarification",intent=state.get('intent'),selected_tool=state.get('selected_tool'),last_user_message=state['messages'][-1].content)
    return {'messages':[AIMessage(content="I am so sorry, i could not understand your previous request. Could you please make your query a bit more clear?")]}

#need to ask for the missing info
def ask_for_missing_info(state:StateAgent):
    debug_print("ask_for_missing_info",selected_tool=state.get('selected_tool'),tool_arguments=state.get('tool_arguments'),missing_arguments=state.get('missing_arguments'))
    missing=", ".join(argument.replace("_"," ") for argument in state['missing_arguments'])
    return {'messages':[AIMessage(content=f"I can look that up, but I still need the following detail(s): {missing}. Please reply with just that information and I will continue.")]}

class Infocheck(TypedDict):
    reason: str
    selected_tool: str | None
    available_arguments: dict
    refers_to_self: bool


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
    - refers_to_self: true if the user is asking about themself ("my", "me", "I", "mine"), otherwise false. Never put the user's own employee id in available_arguments yourself; the application fills it in.
    """
    structured_model=model.with_structured_output(Infocheck)
    try:
        answer=call_with_retry(lambda: structured_model.invoke(prompt), step="tool selection",
                                   retry_on=LLM_RETRY_KINDS,
                                   validate=lambda a: isinstance(a,dict))
    except ServiceError as err:
        return llm_failure("check_for_missing_info", err)
    debug_print("check_for_missing_info: model tool selection",raw_answer=answer)
    selected_tool_name = answer.get("selected_tool")
    selected_tool = next((tool for tool in tools if tool.name == selected_tool_name), None)

    if selected_tool is None:
        debug_print("check_for_missing_info: no matching tool",requested_tool=selected_tool_name,known_tools=list(tools_by_names))
        return {'enough_info':False,'missing_arguments':[],'selected_tool':None,'tool_arguments':{},'refers_to_self':False,'denial_reason':None}

    argument_schema = selected_tool.get_input_schema().model_json_schema()
    required_arguments = argument_schema.get("required", [])
    refers_to_self = bool(answer.get("refers_to_self"))
    available_arguments = resolve_arguments(
        selected_tool.name, answer.get("available_arguments") or {}, state["user"], refers_to_self, required_arguments
    )
    missing_arguments = [
        argument for argument in required_arguments
        if argument not in available_arguments
    ]
    debug_print("check_for_missing_info: argument check",selected_tool=selected_tool.name,tool_description=selected_tool.description,all_parameters=list(argument_schema.get("properties",{})),required_arguments=required_arguments,arguments_from_model=available_arguments,missing_arguments=missing_arguments,enough_info=len(missing_arguments)==0)

    if len(missing_arguments)==0:
        return {'enough_info':True,'missing_arguments':[],'selected_tool':selected_tool.name,'tool_arguments':available_arguments,'refers_to_self':refers_to_self,'denial_reason':None}
    else:
        return {'enough_info':False,'missing_arguments':missing_arguments,'selected_tool':selected_tool.name,'tool_arguments':available_arguments,'refers_to_self':refers_to_self,'denial_reason':None}

#is enough confitional edge for routing
def is_info_enough(state:StateAgent):
    mixed=state['intent']['intent']=="Mixed:have both queries"
    if state["selected_tool"] is None:
        route="final_answer" if mixed else "ask_for_clarification"
    elif state["enough_info"]:
        route="execute_tool"
    else:
        route="final_answer" if mixed else "ask_for_missing_info"
    debug_print("is_info_enough (router)",selected_tool=state["selected_tool"],enough_info=state["enough_info"],missing_arguments=state["missing_arguments"],next_node=route)
    return route

#authorization: runs right after check_for_missing_info, before asking for missing info or executing
def authorize_tool(state:StateAgent):
    if state["selected_tool"] is None:
        return {"denial_reason":None}
    decision=authorize(state["selected_tool"],state["tool_arguments"] or {},state["user"])
    debug_print("authorize_tool",tool=state["selected_tool"],role=state["user"]["role"],arguments=state["tool_arguments"],allowed=decision.allowed,reason=decision.reason)
    return {"denial_reason":None if decision.allowed else decision.reason}

def access_denied(state:StateAgent):
    debug_print("access_denied",reason=state.get("denial_reason"))
    return {"messages":[AIMessage(content=f"Sorry, I can't do that. {state['denial_reason']}")]}

def after_authorization(state:StateAgent):
    if state.get("llm_error"):
        return "final_answer" if state["intent"]["intent"]=="Mixed:have both queries" else END
    if state.get("denial_reason"):
        mixed=state["intent"]["intent"]=="Mixed:have both queries"
        route="final_answer" if mixed else "access_denied"
        debug_print("after_authorization (router)",denial_reason=state["denial_reason"],next_node=route)
        return route
    return is_info_enough(state)

#this after the execute_tool
def execute_tool(state:StateAgent):
    tool = tools_by_names[state["selected_tool"]]
    debug_print("execute_tool: calling",tool=tool.name,arguments=state["tool_arguments"])
    try:
        observation = call_with_retry(
            lambda: tool.invoke(state["tool_arguments"]),
            step=f"tool {tool.name}",
            service="database",
            retry_on=DB_RETRY_KINDS,
        )
        debug_print("execute_tool: success",result_type=type(observation).__name__,result=observation)
    except ServiceError as err:
        if err.kind in ("database", "database_error"):
            observation = f"The database lookup failed: {err.user_message}"
        else:
            observation = f"The database lookup failed: {err.original}"
        debug_print("execute_tool: FAILED",kind=err.kind,error=repr(err.original))
    return {"Database_result": observation}
    
def final_answer(state:StateAgent):
    if state.get("llm_error"):
        return {}
    if state.get("retrieval_error") and not state.get("Database_query"):
        return {"messages":[AIMessage(content="I couldn't search the company handbook right now, so I can't answer that. Please try again in a moment.")]}
    retrieval_note = (
        "The document search failed, so there are no document chunks. Do not guess any policy or handbook content; say that part could not be looked up right now."
        if state.get("retrieval_error")
        else "Document search worked normally."
    )
    question=next((message.content for message in reversed(state['messages']) if isinstance(message, HumanMessage)), "")
    history="\n".join(f"{'User' if isinstance(message,HumanMessage) else 'Assistant'}: {str(message.content)[:500]}" for message in state['messages'][-7:-1]) or "None"
    selected=state.get('selected_tool')
    purpose=tools_by_names[selected].description.strip().split("\n\n")[0] if selected else ""
    result=state.get('Database_result')
    record_count=len(result) if isinstance(result,list) else None
    count_note=f" The tool returned exactly {record_count} records." if record_count is not None else ""
    missing=", ".join(argument.replace("_"," ") for argument in state.get('missing_arguments') or [])
    if state.get('denial_reason'):
        lookup_note=f"The record lookup was refused for this user: {state['denial_reason']} There are no database results. Tell the user this part is not permitted for their role. Do not guess or reveal any record data."
    elif state.get('Database_query') and not selected:
        lookup_note="The record part of the question could not be matched to any available lookup, so there are no database results. Say that this part could not be answered and ask the user to rephrase it."
    elif selected and state.get('enough_info') is False:
        lookup_note=f"The record lookup could not be run because it still needs these details from the user: {missing}. There are no database results. Do not guess the missing values."
    elif selected:
        lookup_note=f"The database results were produced by running the tool {selected} with these arguments: {state.get('tool_arguments')}. Tool purpose: {purpose.rstrip('.')}.{count_note}"
    else:
        lookup_note="No database lookup was performed."
    debug_print("final_answer: input",question=question,earlier_conversation=history,lookup_note=lookup_note,standalone_request=state.get('Database_query'),database_result=state.get('Database_result'),chunks_in_prompt=len(state.get('Retrieved_chunks') or []),chunk_sources=[chunk.metadata.get('source') or chunk.metadata.get('file_path') for chunk in state.get('Retrieved_chunks') or []])
    prompt=f"""
    You are a helpful AI assistant for a company.

    Your task is to answer the user's question using the information
    provided in the database results and retrieved document chunks.

    Earlier conversation (context only, do not answer these old messages again):
    {history}

    User's latest question:
    {question}

    Database results:
    {state.get('Database_result')}

    How the database results were produced:
    {lookup_note}

    Retrieved document chunks:
    {state.get('Retrieved_chunks')}

    Document search status:
    {retrieval_note}

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
    7. If the database results are a list, include EVERY record in your answer, one after another, and do not stop early or skip any. State the total number of records exactly as given in the lookup note. Do not make claims about date ranges or years that have no records unless the results show it.
    8. If the note says the record lookup could not be run or matched, first answer the part of the question that the retrieved chunks can answer, then ask the user in one short sentence for what is needed to complete the rest. Never present the missing part as answered.
    9. If the latest question refers to something said earlier (for example "what about her?", or it only supplies a detail you asked for), use the earlier conversation to understand what is being asked. Take facts only from the database results and the retrieved chunks, never from the earlier conversation.
    """

    try:
        response=call_with_retry(
            lambda: model.invoke(prompt),
            step="final answer",
            retry_on=LLM_RETRY_KINDS,
            validate=lambda r: bool(str(getattr(r, "content", "")).strip()),
        )
    except ServiceError as err:
        return llm_failure("final_answer", err)
    debug_print("final_answer: output",answer=response.content,usage=getattr(response,'usage_metadata',None))
    if (state['intent']['intent'] == "RAG_Query"
            and state.get("Rag_query")
            and state.get("Retrieved_chunks")
            and not state.get("retrieval_error")):
        cache_store(state["Rag_query"], response.content)
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
graph.add_node("final_answer", final_answer, defer=True)
graph.add_node("not_implemented_yet", not_implemented_yet)
graph.add_node("handle_irrelevant_query", handle_irrelevant_query)
graph.add_node("RAG_Query_Retrieval", RAG_Query_Retrieval)
graph.add_node("authorize_tool", authorize_tool)
graph.add_node("access_denied", access_denied)
graph.add_node("check_cache", check_cache)

# Start directly with the query already provided in state
graph.add_edge(START, "Intent Classification")

graph.add_conditional_edges(
    "Intent Classification",
    intent_router
)
graph.add_conditional_edges("check_cache", after_cache_check)
graph.add_edge("check_for_missing_info", "authorize_tool")
graph.add_conditional_edges(
    "authorize_tool",
    after_authorization
)

graph.add_edge("execute_tool", "final_answer")
graph.add_edge("RAG_Query_Retrieval", "final_answer")

# These nodes return a response to the outer loop.
# The next user input is collected by the Python loop.
graph.add_edge("ask_for_clarification", END)
graph.add_edge("access_denied", END)
graph.add_edge("ask_for_missing_info", END)
graph.add_edge("not_implemented_yet", END)
graph.add_edge("handle_irrelevant_query", END)
graph.add_edge("final_answer", END)

app=graph.compile()
messages=[]
def load_user_by_email(email: str) -> User | None:
    
    stmt = (
        select(
            Employees.employee_id,
            Employees.first_name,
            Employees.last_name,
            Employees.gender,
            Employees.email,
            Employees.phone_number,
            Employees.date_joined,
            Employees.job_title,
            Employees.employment_status,
            Employees.role,
            Department.name.label("department_name"),
            Employees.manager_id,
        )
        .join(
            Department,
            Employees.department_id == Department.department_id,
        )
        .where(Employees.email == email)
    )

    with SessionLocal() as session:
        result = session.execute(stmt).mappings().one_or_none()

    if result is None:
        return None

    return dict(result)

def login():
    while True:
        email = input("Login email (or 'exit'): ").strip()
        if email.lower() in ("exit", "quit"):
            return None
        try:
            user = call_with_retry(
                lambda: load_user_by_email(email),
                step="login",
                service="database",
                retry_on=DB_RETRY_KINDS,
            )
        except ServiceError as err:
            print(f"Assistant: {err.user_message}")
            continue
        if user is None:
            print("Assistant: I couldn't find an employee with that email. Please try again.")
            continue
        return user

if __name__ == "__main__":
    RECORD_TRACE = True
    purge_stale()
    messages = []
    user = login()
    if user is None:
        raise SystemExit

    while True:
        try:
            query = input("You: ")
        except (KeyboardInterrupt, EOFError):
            break

        if query.lower() in ["exit", "quit"]:
            break
        if not query.strip():
            continue

        messages.append(HumanMessage(content=query))

        trace.clear()
        try:
            result = app.invoke({"messages": messages, "user": user})
        except KeyboardInterrupt:
            messages.pop()
            print("\nCancelled.")
            continue
        except Exception:
            logger.exception("Unhandled error while processing the query")
            messages.pop()
            print("Assistant: Sorry, something went wrong on my side while handling that. Please try again.")
            continue

        debug_print(
            "turn summary",
            nodes_visited=" -> ".join(trace),
            intent=(result.get("intent") or {}).get("intent"),
            cache_hit=result.get("cache_hit"),
            selected_tool=result.get("selected_tool"),
            tool_arguments=result.get("tool_arguments"),
            chunks_retrieved=len(result.get("Retrieved_chunks") or []),
            total_messages=len(result["messages"]),
        )
        messages = result["messages"]

        print("Assistant:", messages[-1].content)