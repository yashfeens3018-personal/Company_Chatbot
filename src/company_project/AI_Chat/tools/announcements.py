from datetime import datetime

from langchain.tools import tool

from ...queries.announcements import (
    get_announcement,
    search_announcements,
    get_active_announcements,
    get_department_announcements,
    get_employee_announcements,
)


@tool
def get_announcement_tool(announcement_id: int):
    """Fetch ONE announcement by its numeric announcement ID.

    Use this ONLY when the user gave an announcement ID (e.g. "announcement
    12"). If the user gave a title, a topic, a keyword, a department, or an
    author, do NOT use this tool; use ``search_announcements_tool`` instead.
    Never guess an ID.

    Returns the announcement's title, content, creator, department,
    publish date, and expiry date.

    Args:
        announcement_id: Numeric announcement ID (integer greater than 0).
    """
    return get_announcement(announcement_id)


@tool
def search_announcements_tool(
    title: str | None = None,
    content: str | None = None,
    created_by: int | None = None,
    department_name: str | None = None,
    published_from: datetime | None = None,
    published_to: datetime | None = None,
    expires_from: datetime | None = None,
    expires_to: datetime | None = None,
):
    """Find announcements WITHOUT an ID: by title, topic, creator, department, or dates.

    This is the default tool for any announcement request that does not
    include an announcement ID. Returns a list of matching announcements
    (title, content, creator, department, publish date, expiry date). A single
    match is still returned as a list. With NO arguments it returns ALL
    announcements. All filters are optional and combined with AND.

    Choosing title vs content:
    - Use ``title`` when the user says the announcement is "named", "titled",
      "called", or gives its exact heading.
      Example: 'the announcement named "Laptops Now Available"' ->
      title="Laptops Now Available".
    - Use ``content`` when the user asks for announcements "about" or
      "mentioning" a topic or word. Example: "announcements about laptops" ->
      content="laptops".
    - If unsure which one the user means, prefer ``content`` for a topic and
      ``title`` for a quoted name.

    Args:
        title: Text to match against the announcement title (case-insensitive).
        content: Text to match against the announcement body.
        created_by: Employee ID of the author (integer).
        department_name: Exact name of the department the announcement
            belongs to. The query resolves its department ID internally.
        published_from: Only announcements published on or after this
            timestamp (ISO 8601).
        published_to: Only announcements published on or before this timestamp.
        expires_from: Only announcements expiring on or after this timestamp.
        expires_to: Only announcements expiring on or before this timestamp.
    """
    return search_announcements(
        title=title,
        content=content,
        created_by=created_by,
        department_name=department_name,
        published_from=published_from,
        published_to=published_to,
        expires_from=expires_from,
        expires_to=expires_to,
    )


@tool
def get_active_announcements_tool(department_name: str | None = None):
    """List announcements that are currently active (published and not yet expired).

    Use for "current", "active", "latest", or "valid right now" announcements.
    Do not use for expired or historical announcements, or for finding one by
    title or topic (use ``search_announcements_tool``).

    Args:
        department_name: Optional exact department name. If given, active
            announcements for that department and company-wide active
            announcements are returned; if omitted, all active announcements
            are returned.
    """
    return get_active_announcements(department_name=department_name)


@tool
def get_department_announcements_tool(
    department_name: str,
    include_expired: bool = True,
):
    """List announcements posted by one department, using its name.

    Use when the user asks for announcements associated with a department.
    The query resolves the department ID from this name internally.

    Args:
        department_name: Exact department name.
        include_expired: True (default) returns active AND expired
            announcements. Set False only if the user wants just the
            currently active ones.
    """
    return get_department_announcements(
        department_name=department_name,
        include_expired=include_expired,
    )


@tool
def get_employee_announcements_tool(first_name: str, last_name: str):
    """List announcements written by employees with the given full name.

    Use when the user asks what an employee has announced and provides their
    first and last name. Employee IDs are resolved internally. If multiple
    employees share that full name, announcements from all of them are
    returned.

    Args:
        first_name: Employee's exact first name; matching ignores case.
        last_name: Employee's exact last name; matching ignores case.

    Returns:
        A list of matching announcements with announcement ID, title,
        content, department name, publish date, expiry date, and creator ID.
        Raises LookupError if no employee has the supplied full name.
    """
    return get_employee_announcements(
        first_name=first_name,
        last_name=last_name,
    )