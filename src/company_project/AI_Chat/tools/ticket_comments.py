from datetime import datetime

from langchain.tools import tool

from ...queries.ticket_comments import (
    get_comment,
    get_comment_count,
    get_latest_ticket_comment,
    get_ticket_comments,
    search_ticket_comments,
)


@tool
def get_comment_tool(comment_id: int):
    """Retrieve a ticket comment by its comment ID.

    Returns the comment ID, ticket ID, author ID, comment text, and creation
    timestamp. Raises a not-found error if the comment does not exist.

    Args:
        comment_id: ID of the comment to retrieve.
    """
    return get_comment(comment_id=comment_id)


@tool
def get_ticket_comments_tool(ticket_id: int):
    """List all comments on a ticket in chronological order.

    Returns each comment's ID, ticket ID, author ID, text, and creation
    timestamp. The ticket must exist; a ticket with no comments returns an
    empty list.

    Args:
        ticket_id: ID of the ticket whose comments should be retrieved.
    """
    return get_ticket_comments(ticket_id=ticket_id)


@tool
def search_ticket_comments_tool(
    ticket_id: int | None = None,
    author_id: int | None = None,
    comment: str | None = None,
    created_from: datetime | None = None,
    created_to: datetime | None = None,
):
    """Search ticket comments by ticket, author, text, or creation date.

    Returns matching comments ordered from oldest to newest, with comment ID,
    ticket ID, author ID, text, and creation timestamp. Text matching is
    case-insensitive and partial. If supplied, the ticket and author must
    exist. Date bounds are inclusive, and ``created_from`` cannot be later
    than ``created_to``. With no filters, returns all comments.

    Args:
        ticket_id: Optional ticket ID to filter comments.
        author_id: Optional employee ID of the comment author.
        comment: Optional case-insensitive partial match against comment text.
        created_from: Inclusive earliest comment creation timestamp.
        created_to: Inclusive latest comment creation timestamp.
    """
    return search_ticket_comments(
        ticket_id=ticket_id,
        author_id=author_id,
        comment=comment,
        created_from=created_from,
        created_to=created_to,
    )


@tool
def get_latest_ticket_comment_tool(ticket_id: int):
    """Retrieve the most recently created comment on a ticket.

    Returns a one-item list containing the latest comment's ID, ticket ID,
    author ID, text, and creation timestamp. The ticket must exist. If the
    ticket has no comments, returns an empty list.

    Args:
        ticket_id: ID of the ticket whose latest comment should be retrieved.
    """
    return get_latest_ticket_comment(ticket_id=ticket_id)


@tool
def get_comment_count_tool(ticket_id: int):
    """Count the comments attached to a ticket.

    Returns the comment count for the ticket. The ticket must exist; a ticket
    with no comments has a count of zero.

    Args:
        ticket_id: ID of the ticket whose comments should be counted.
    """
    return get_comment_count(ticket_id=ticket_id)