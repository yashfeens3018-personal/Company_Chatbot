"""
Authorization rules for the company assistant.

Two levels of control, enforced in plain Python (never by the LLM):
  1. TOOL access      -> which roles may call a tool at all          ("roles")
  2. DATA access      -> which argument values a role may pass       ("self_arg" + "self_only_unless")
     Roles NOT in `self_only_unless` may only pass their OWN employee id for `self_arg`.

"Me" logic: the LLM only says whether the user is talking about themself
(refers_to_self). The id itself always comes from the logged-in user in state,
never from the LLM.
"""
from dataclasses import dataclass

ADMIN, HR, IT, FINANCE, EMPLOYEE = "admin", "hr", "it", "finance", "employee"
ALL_ROLES = {ADMIN, HR, IT, FINANCE, EMPLOYEE}

# ---- Role groups (edit these in one place) ----
ASSET_FULL_ACCESS = {ADMIN, IT, FINANCE}
TICKET_FULL_ACCESS = {ADMIN, IT}
LEAVE_FULL_ACCESS = {ADMIN, HR}


def open_tool(self_arg=None):
    """Everyone may use it with any argument."""
    return {"roles": ALL_ROLES, "self_arg": self_arg, "self_only_unless": None}


def restricted_tool(roles):
    """Only `roles` may use it, with any argument."""
    return {"roles": set(roles), "self_arg": None, "self_only_unless": None}


def own_data_tool(full_access, self_arg="employee_id"):
    """Everyone may use it, but roles outside `full_access` can only pass their own id."""
    return {"roles": ALL_ROLES, "self_arg": self_arg, "self_only_unless": set(full_access)}


POLICIES = {
    # 1. Announcements: everyone, any argument
    "get_announcement_tool":             open_tool(),
    "search_announcements_tool":         open_tool(),
    "get_active_announcements_tool":     open_tool(),
    "get_department_announcements_tool": open_tool(),
    "get_employee_announcements_tool":   open_tool("employee_id"),

    # 2. Assets: admin/it/finance full; everyone else only their own assets
    "get_asset_tool":               restricted_tool(ASSET_FULL_ACCESS),
    "get_asset_stats_tool":         restricted_tool(ASSET_FULL_ACCESS),
    "get_expiring_warranties_tool": restricted_tool(ASSET_FULL_ACCESS),
    "get_unassigned_assets_tool":   restricted_tool(ASSET_FULL_ACCESS),
    "search_assets_tool":           restricted_tool(ASSET_FULL_ACCESS),
    "get_employee_assets_tool":     own_data_tool(ASSET_FULL_ACCESS),

    # 3. Departments: everyone, any argument
    "get_department_info_tool": open_tool(),
    "get_departments_tool":     open_tool(),

    # 4. Employees: everyone, any argument
    "get_employee_tool":       open_tool("employee_id"),
    "search_employees_tool":   open_tool(),
    "get_employee_stats_tool": open_tool(),

    # 5. Projects and project members: everyone, any argument
    "get_employee_projects_tool":            open_tool("employee_id"),
    "get_project_tool":                      open_tool(),
    "get_project_stats_tool":                open_tool(),
    "search_projects_tool":                  open_tool(),
    "get_employee_project_memberships_tool": open_tool("employee_id"),
    "get_project_member_tool":               open_tool(),
    "get_project_members_tool":              open_tool(),
    "search_project_members_tool":           open_tool(),

    # 6. Tickets: admin/it full; everyone else only their own created/assigned tickets
    "get_ticket_tool":                   restricted_tool(TICKET_FULL_ACCESS),
    "get_ticket_stats_tool":             restricted_tool(TICKET_FULL_ACCESS),
    "search_tickets_tool":               restricted_tool(TICKET_FULL_ACCESS),
    "get_employee_created_tickets_tool":  own_data_tool(TICKET_FULL_ACCESS),
    "get_employee_assigned_tickets_tool": own_data_tool(TICKET_FULL_ACCESS),

    # 7. Ticket comments: follow ticket access (comments expose ticket content)
    "get_comment_tool":               restricted_tool(TICKET_FULL_ACCESS),
    "get_ticket_comments_tool":       restricted_tool(TICKET_FULL_ACCESS),
    "search_ticket_comments_tool":    restricted_tool(TICKET_FULL_ACCESS),
    "get_latest_ticket_comment_tool": restricted_tool(TICKET_FULL_ACCESS),
    "get_comment_count_tool":         restricted_tool(TICKET_FULL_ACCESS),

    # 8. Leave: admin/hr full; everyone else only their own balance and employment info
    "get_leave_balance_tool":        own_data_tool(LEAVE_FULL_ACCESS),
    "search_leave_balances_tool":    own_data_tool(LEAVE_FULL_ACCESS),
    "get_employment_tool":           own_data_tool(LEAVE_FULL_ACCESS),
    "get_leave_request_tool":        restricted_tool(LEAVE_FULL_ACCESS),
    "search_leave_requests_tool":    {**restricted_tool(LEAVE_FULL_ACCESS), "self_arg": "employee_id"},
}
# Any tool missing from POLICIES is DENIED by default.


@dataclass
class Decision:
    allowed: bool
    reason: str = ""


def _is_restricted(policy, user) -> bool:
    """True if this user may only touch their own data through this tool."""
    unless = policy.get("self_only_unless")
    return unless is not None and user["role"] not in unless


def resolve_arguments(tool_name, args, user, refers_to_self, required_args=()):
    """Apply the 'me' logic. Call BEFORE checking for missing arguments.

    - User said "my/me/I"          -> self_arg is set to the logged-in user's id
                                      (overrides anything the LLM guessed).
    - Restricted user, optional
      self_arg left out            -> forced to their own id so a search can never
                                      widen to other employees.
    - Required self_arg left out
      and not "me"                 -> stays missing, so the bot asks for it
                                      (and authorize() will refuse other people's ids).
    """
    args = dict(args or {})
    policy = POLICIES.get(tool_name)
    if not policy or not policy.get("self_arg"):
        return args
    arg = policy["self_arg"]
    if refers_to_self:
        args[arg] = user["employee_id"]
    elif _is_restricted(policy, user) and arg not in args and arg not in required_args:
        args[arg] = user["employee_id"]
    return args


def authorize(tool_name, args, user) -> Decision:
    """Level 1 (tool) and level 2 (argument) check."""
    policy = POLICIES.get(tool_name)
    role = user.get("role")
    if policy is None:
        return Decision(False, f"No access rule is defined for '{tool_name}'.")
    if role not in policy["roles"]:
        return Decision(False, f"Your role ({role}) is not allowed to use this lookup.")
    if _is_restricted(policy, user):
        arg = policy["self_arg"]
        value = (args or {}).get(arg)
        if value is not None and str(value) != str(user["employee_id"]):
            return Decision(False, "You can only access your own records with this lookup.")
    return Decision(True)


def validate_policies(tools_by_names):
    """Run once at startup. Catches name typos and wrong argument names."""
    missing = [n for n in tools_by_names if n not in POLICIES]
    unknown = [n for n in POLICIES if n not in tools_by_names]
    if missing:
        print("WARNING: tools with NO policy (will be denied):", missing)
    if unknown:
        print("WARNING: policies for tools that don't exist:", unknown)
    for name, policy in POLICIES.items():
        tool = tools_by_names.get(name)
        arg = policy.get("self_arg")
        if tool and arg and arg not in tool.args:
            print(f"WARNING: '{name}' has no argument '{arg}' (its args: {list(tool.args)}). "
                  f"Fix self_arg in POLICIES.")