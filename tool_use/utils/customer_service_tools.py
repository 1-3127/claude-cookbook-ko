"""
Claude용 고객 서비스 Tool
지원 ticket 처리용 tool 함수 구현
"""

import json
from typing import Literal

from anthropic import beta_tool

from .customer_service_api import (
    KNOWLEDGE_BASE,
    TEAM_ROUTING,
    Ticket,
    TicketCategory,
    TicketGenerator,
    TicketPriority,
    TicketStatus,
)

# Demo용 전역 상태 — production에서는 database 사용
_ticket_queue: list[Ticket] = []
_current_tickets: dict[str, Ticket] = {}
_queue_index = 0


def initialize_ticket_queue(count: int = 25):
    """생성한 ticket으로 ticket queue를 초기화합니다."""
    global _ticket_queue, _queue_index, _current_tickets
    _ticket_queue = TicketGenerator.generate_batch(count)
    _queue_index = 0
    _current_tickets = {}


def _get_ticket(ticket_id: str) -> Ticket | None:
    """ID로 ticket을 가져오는 helper"""
    return _current_tickets.get(ticket_id)


def _serialize_ticket(ticket: Ticket) -> str:
    """Ticket을 JSON string으로 변환합니다."""
    return json.dumps(
        {
            "id": ticket.id,
            "customer_name": ticket.customer_name,
            "customer_email": ticket.customer_email,
            "subject": ticket.subject,
            "description": ticket.description,
            "category": ticket.category.value if ticket.category else None,
            "priority": ticket.priority.value if ticket.priority else None,
            "status": ticket.status.value,
            "created_at": ticket.created_at.isoformat() if ticket.created_at else None,
            "assigned_team": ticket.assigned_team,
            "notes": ticket.notes,
        },
        indent=2,
    )


@beta_tool
def get_next_ticket() -> str:
    """
    Queue에서 다음 미처리 ticket을 가져옵니다.
    Ticket 세부 사항을 JSON string으로 반환합니다.
    """
    global _queue_index

    if _queue_index >= len(_ticket_queue):
        return json.dumps(
            {
                "error": "No more tickets in queue",
                "processed": _queue_index,
                "total": len(_ticket_queue),
            }
        )

    ticket = _ticket_queue[_queue_index]
    _queue_index += 1
    _current_tickets[ticket.id] = ticket

    return _serialize_ticket(ticket)


@beta_tool
def classify_ticket(
    ticket_id: str, category: Literal["billing", "technical", "account", "product", "shipping"]
) -> str:
    """
    Ticket을 category로 분류합니다.

    Args:
        ticket_id: Ticket ID
        category: 지정할 category

    Returns:
        확인 message
    """
    ticket = _get_ticket(ticket_id)
    if not ticket:
        return json.dumps({"error": f"Ticket {ticket_id} not found"})

    ticket.category = TicketCategory(category)

    return json.dumps(
        {
            "success": True,
            "message": f"Ticket {ticket_id} classified as {category}",
            "ticket_id": ticket_id,
        }
    )


@beta_tool
def search_knowledge_base(category: str, query: str) -> str:
    """
    Knowledge base에서 관련 정보를 검색합니다.

    Args:
        category: 검색할 category (billing, technical, account)
        query: 검색할 keyword

    Returns:
        관련 knowledge base 문서의 JSON
    """
    category_lower = category.lower()

    if category_lower not in KNOWLEDGE_BASE:
        return json.dumps(
            {
                "error": f"Category '{category}' not found",
                "available_categories": list(KNOWLEDGE_BASE.keys()),
            }
        )

    category_kb = KNOWLEDGE_BASE[category_lower]

    # 간단한 keyword 검색
    query_lower = query.lower()
    results = {}

    for key, value in category_kb.items():
        if isinstance(value, dict):
            # 중첩 dictionary 검색
            for sub_key, sub_value in value.items():
                if query_lower in sub_key.lower() or query_lower in str(sub_value).lower():
                    if key not in results:
                        results[key] = {}
                    results[key][sub_key] = sub_value
        else:
            # 평면 key-value 쌍 검색
            if query_lower in key.lower() or query_lower in value.lower():
                results[key] = value

    return json.dumps(
        {
            "category": category,
            "query": query,
            "results": results if results else category_kb,
            "all_available": category_kb,
        },
        indent=2,
    )


@beta_tool
def set_priority(ticket_id: str, priority: Literal["low", "medium", "high", "urgent"]) -> str:
    """
    Ticket의 priority level을 설정합니다.

    Args:
        ticket_id: Ticket ID
        priority: Priority level

    Returns:
        확인 message
    """
    ticket = _get_ticket(ticket_id)
    if not ticket:
        return json.dumps({"error": f"Ticket {ticket_id} not found"})

    old_priority = ticket.priority.value if ticket.priority else "unset"
    ticket.priority = TicketPriority(priority)

    return json.dumps(
        {
            "success": True,
            "message": f"Ticket {ticket_id} priority updated from {old_priority} to {priority}",
            "ticket_id": ticket_id,
            "old_priority": old_priority,
            "new_priority": priority,
        }
    )


@beta_tool
def route_to_team(ticket_id: str, team: str) -> str:
    """
    Ticket을 적절한 지원 팀으로 routing합니다.

    Args:
        ticket_id: Ticket ID
        team: 팀 이름 (billing-team, tech-support, account-services, product-success, logistics-team)

    Returns:
        확인 message
    """
    ticket = _get_ticket(ticket_id)
    if not ticket:
        return json.dumps({"error": f"Ticket {ticket_id} not found"})

    valid_teams = list(TEAM_ROUTING.values())
    if team not in valid_teams:
        return json.dumps(
            {
                "error": f"Invalid team '{team}'",
                "valid_teams": valid_teams,
            }
        )

    old_team = ticket.assigned_team
    ticket.assigned_team = team
    ticket.status = TicketStatus.OPEN

    return json.dumps(
        {
            "success": True,
            "message": f"Ticket {ticket_id} routed to {team}",
            "ticket_id": ticket_id,
            "old_team": old_team,
            "new_team": team,
        }
    )


@beta_tool
def draft_response(ticket_id: str, response: str) -> str:
    """
    고객에게 보낼 응답 초안을 작성합니다.

    Args:
        ticket_id: Ticket ID
        response: 응답 초안 텍스트

    Returns:
        초안 저장 확인
    """
    ticket = _get_ticket(ticket_id)
    if not ticket:
        return json.dumps({"error": f"Ticket {ticket_id} not found"})

    # 특수 prefix를 사용해 notes에 초안 저장
    draft_note = f"[DRAFT RESPONSE] {response}"
    ticket.notes.append(draft_note)

    return json.dumps(
        {
            "success": True,
            "message": f"Draft response saved for ticket {ticket_id}",
            "ticket_id": ticket_id,
            "draft_length": len(response),
        }
    )


@beta_tool
def add_note(ticket_id: str, note: str) -> str:
    """
    Ticket에 내부 메모를 추가합니다.

    Args:
        ticket_id: Ticket ID
        note: 팀 참고용 내부 메모

    Returns:
        확인 message
    """
    ticket = _get_ticket(ticket_id)
    if not ticket:
        return json.dumps({"error": f"Ticket {ticket_id} not found"})

    ticket.notes.append(note)

    return json.dumps(
        {
            "success": True,
            "message": f"Note added to ticket {ticket_id}",
            "ticket_id": ticket_id,
            "total_notes": len(ticket.notes),
        }
    )


@beta_tool
def mark_complete(ticket_id: str) -> str:
    """
    Ticket을 처리 완료 및 팀 검토 준비 상태로 표시합니다.

    Args:
        ticket_id: Ticket ID

    Returns:
        Ticket 처리 확인 및 요약
    """
    ticket = _get_ticket(ticket_id)
    if not ticket:
        return json.dumps({"error": f"Ticket {ticket_id} not found"})

    # Ticket을 완료할 준비가 되었는지 검증
    if not ticket.category:
        return json.dumps({"error": "Cannot complete ticket without category classification"})

    if not ticket.priority:
        return json.dumps({"error": "Cannot complete ticket without priority assignment"})

    if not ticket.assigned_team:
        return json.dumps({"error": "Cannot complete ticket without team routing"})

    ticket.status = TicketStatus.RESOLVED

    summary = {
        "success": True,
        "message": f"Ticket {ticket_id} marked complete",
        "ticket_id": ticket_id,
        "summary": {
            "customer": ticket.customer_name,
            "subject": ticket.subject,
            "category": ticket.category.value,
            "priority": ticket.priority.value,
            "assigned_team": ticket.assigned_team,
            "total_notes": len(ticket.notes),
            "status": ticket.status.value,
        },
    }

    return json.dumps(summary, indent=2)


# Demo/테스트용 helper 함수
def get_all_tools():
    """Anthropic API 등록용 tool 함수 전체를 반환합니다."""
    return [
        get_next_ticket,
        classify_ticket,
        search_knowledge_base,
        set_priority,
        route_to_team,
        draft_response,
        add_note,
        mark_complete,
    ]
