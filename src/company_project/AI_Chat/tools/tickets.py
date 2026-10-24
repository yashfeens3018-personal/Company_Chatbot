from datetime import datetime

from langchain.tools import tool

from ...queries.tickets import (
    get_ticket,
    get_ticket_stats,
    get_unassigned_tickets,
    search_tickets,
)


@tool
def get_ticket_tool(ticket_id: int):
    """Retrieve a ticket by its ID.

    Returns a list containing the ticket ID, title, description, category,
    status, priority, creation and update timestamps, due, resolved, and
    closed timestamps, creator ID, and assignee ID. Returns an empty list if
    no ticket has the requested ID.

    Args:
        ticket_id: ID of the ticket to retrieve.
    """
    return get_ticket(ticket_id=ticket_id)


@tool
def search_tickets_tool(
    assigned_to: int | None = None,
    created_by: int | None = None,
    status: str | None = None,
    priority: str | None = None,
    category: str | None = None,
    title: str | None = None,
    description: str | None = None,
    created_from: datetime | None = None,
    created_to: datetime | None = None,
    resolved_from: datetime | None = None,
    resolved_to: datetime | None = None,
    closed_from: datetime | None = None,
    closed_to: datetime | None = None,
):
    """Search tickets by assignee, creator, state, text, and lifecycle dates.

    Returns matching tickets with ID, title, category, status, priority,
    creation, due, resolution, and closure timestamps, creator ID, and
    assignee ID. Status must be open, in progress, pending, resolved, or
    closed; priority must be low, medium, high, or critical. Category must be
    one of it_support, hr, finance, facilities, access_request, software,
    hardware, network, security, payroll, leave, or other. These values are
    matched without regard to case. Title and description filters are
    case-insensitive partial matches. Date filters are inclusive. Supplied
    creator and assignee IDs must belong to existing employees. With no
    filters, returns all tickets.

    Args:
        assigned_to: Optional employee ID assigned to the ticket.
        created_by: Optional employee ID who created the ticket.
        status: Optional status: open, in progress, pending, resolved, or
            closed.
        priority: Optional priority: low, medium, high, or critical.
        category: Optional category: it_support, hr, finance, facilities,
            access_request, software, hardware, network, security, payroll,
            leave, or other.
        title: Optional case-insensitive partial match for the ticket title.
        description: Optional case-insensitive partial match for the ticket
            description.
        created_from: Inclusive earliest ticket creation timestamp.
        created_to: Inclusive latest ticket creation timestamp.
        resolved_from: Inclusive earliest ticket resolution timestamp.
        resolved_to: Inclusive latest ticket resolution timestamp.
        closed_from: Inclusive earliest ticket closure timestamp.
        closed_to: Inclusive latest ticket closure timestamp.
    """
    return search_tickets(
        assigned_to=assigned_to,
        created_by=created_by,
        status=status,
        priority=priority,
        category=category,
        title=title,
        description=description,
        created_from=created_from,
        created_to=created_to,
        resolved_from=resolved_from,
        resolved_to=resolved_to,
        closed_from=closed_from,
        closed_to=closed_to,
    )


@tool
def get_unassigned_tickets_tool(
    status: str | None = None,
    priority: str | None = None,
    category: str | None = None,
):
    """List tickets that have no assignee, optionally filtered by ticket fields.

    Returns each ticket's ID, title, category, status, priority, creation
    timestamp, and due timestamp. Optional status, priority, and category
    values are validated against the same allowed values as ticket search;
    matching is case-insensitive. With no filters, returns all unassigned
    tickets.

    Args:
        status: Optional status: open, in progress, pending, resolved, or
            closed.
        priority: Optional priority: low, medium, high, or critical.
        category: Optional category: it_support, hr, finance, facilities,
            access_request, software, hardware, network, security, payroll,
            leave, or other.
    """
    return get_unassigned_tickets(
        status=status,
        priority=priority,
        category=category,
    )


@tool
def get_ticket_stats_tool(
    assigned_to: int | None = None,
    created_by: int | None = None,
    status: str | None = None,
    priority: str | None = None,
    category: str | None = None,
    created_from: datetime | None = None,
    created_to: datetime | None = None,
):
    """Count tickets matching optional owner, classification, and creation-date filters.

    Returns the total ticket count for the supplied filters. Status must be
    open, in progress, pending, resolved, or closed; priority must be low,
    medium, high, or critical; and category must be one of it_support, hr,
    finance, facilities, access_request, software, hardware, network,
    security, payroll, leave, or other. These values are matched without
    regard to case. Supplied creator and assignee IDs must belong to existing
    employees. Creation-date bounds are inclusive. With no filters, counts
    all tickets.

    Args:
        assigned_to: Optional employee ID assigned to the ticket.
        created_by: Optional employee ID who created the ticket.
        status: Optional status: open, in progress, pending, resolved, or
            closed.
        priority: Optional priority: low, medium, high, or critical.
        category: Optional supported ticket category.
        created_from: Inclusive earliest ticket creation timestamp.
        created_to: Inclusive latest ticket creation timestamp.
    """
    return get_ticket_stats(
        assigned_to=assigned_to,
        created_by=created_by,
        status=status,
        priority=priority,
        category=category,
        created_from=created_from,
        created_to=created_to,
    )