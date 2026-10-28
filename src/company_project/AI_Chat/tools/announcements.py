from langchain.tools import tool
from ...queries.announcements import get_announcement, search_announcements,get_active_announcements,get_department_announcements,get_employee_announcements
from datetime import datetime


@tool
def get_announcement_tool(announcement_id:int):
    """Retrieve ONE announcement when you already have its exact announcement ID.
    Do not use this to list or browse announcements; use search_announcements_tool for that."""
    return get_announcement(announcement_id)

@tool
def search_announcements_tool(title:str=None,
    content:str=None,
    created_by:int=None,
    department_id:int=None,
    published_from:datetime=None,
    published_to:datetime=None,
    expires_from:datetime=None,
    expires_to:datetime=None):
    """List or search announcements and can also give u a single announcement. Call with NO arguments to list ALL announcements,
    or filter by title, content, creator, department, publish date range or expiry date range.
    Use this whenever the user does not give an announcement ID."""
    return search_announcements(title,
    content,
    created_by,
    department_id,
    published_from,
    published_to,
    expires_from,
    expires_to)
    
@tool
def get_active_announcements_tool(department_id:int=None):
    """Retrieves a list of all announcements which are not due or in other words are active right now
    Args:
        department_id (int, optional): _description_. Defaults to None.
    """
    return get_active_announcements(department_id)

@tool
def get_department_announcements_tool(department_id:int,
    include_expired:bool=True):
    """
    Retrieves the announcements done by a department and can include the due and expired announcements too if user wants. 
    Args:
        department_id (int): _description_
        include_expired (bool, optional): _description_. Defaults to False.
    """
    return get_department_announcements(department_id, include_expired)

@tool
def get_employee_announcements_tool(employee_id:int):
    """
    Get all the announcements made by an employee by his employee_id

    Args:
        employee_id (int): _description_
    """
    return get_employee_announcements(employee_id)

