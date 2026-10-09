"""
팀 지출 관리 Demo용 Mock API 예제

Programmatic tool calling cookbook에 사용하는 domain-specific API입니다.
팀 구성원 정보, 지출 기록, 직원 level별 budget limit를 가져오는
mock tool을 제공합니다.
"""

import json
import random
import time
from datetime import datetime, timedelta

# Configuration
EXPENSE_LINE_ITEMS_PER_PERSON_MIN = 20
EXPENSE_LINE_ITEMS_PER_PERSON_MAX = 50
DELAY_MULTIPLIER = 0  # API latency를 모사하려면 조정


def get_team_members(department: str) -> str:
    """지정한 부서의 팀 구성원 목록을 반환합니다.

    각 구성원에는 ID, 이름, role, level, 연락처가 포함됩니다.
    지출을 분석할 사람들의 목록을 가져올 때 사용합니다.

    Args:
        department: 부서 이름 (예: 'engineering', 'sales', 'marketing').
            대소문자를 구분하지 않습니다.

    Returns:
        다음 field를 가진 팀 구성원 object 배열의 JSON string:
        - id: 직원의 고유 식별자
        - name: 전체 이름
        - role: 직무명
        - level: 직원 level (junior, mid, senior, staff, principal)
        - email: 연락용 email
        - department: 부서 이름
    """
    import time

    time.sleep(DELAY_MULTIPLIER * 0.1)

    department = department.lower()

    # 부서별 mock 팀 데이터
    teams = {
        "engineering": [
            {
                "id": "ENG001",
                "name": "Alice Chen",
                "role": "Senior Software Engineer",
                "level": "senior",
                "email": "alice.chen@company.com",
                "department": "engineering",
            },
            {
                "id": "ENG002",
                "name": "Bob Martinez",
                "role": "Staff Engineer",
                "level": "staff",
                "email": "bob.martinez@company.com",
                "department": "engineering",
            },
            {
                "id": "ENG003",
                "name": "Carol White",
                "role": "Software Engineer",
                "level": "mid",
                "email": "carol.white@company.com",
                "department": "engineering",
            },
            {
                "id": "ENG004",
                "name": "David Kim",
                "role": "Principal Engineer",
                "level": "principal",
                "email": "david.kim@company.com",
                "department": "engineering",
            },
            {
                "id": "ENG005",
                "name": "Emma Johnson",
                "role": "Junior Software Engineer",
                "level": "junior",
                "email": "emma.johnson@company.com",
                "department": "engineering",
            },
            {
                "id": "ENG006",
                "name": "Frank Liu",
                "role": "Senior Software Engineer",
                "level": "senior",
                "email": "frank.liu@company.com",
                "department": "engineering",
            },
            {
                "id": "ENG007",
                "name": "Grace Taylor",
                "role": "Software Engineer",
                "level": "mid",
                "email": "grace.taylor@company.com",
                "department": "engineering",
            },
            {
                "id": "ENG008",
                "name": "Henry Park",
                "role": "Staff Engineer",
                "level": "staff",
                "email": "henry.park@company.com",
                "department": "engineering",
            },
        ],
        "sales": [
            {
                "id": "SAL001",
                "name": "Irene Davis",
                "role": "Account Executive",
                "level": "mid",
                "email": "irene.davis@company.com",
                "department": "sales",
            },
            {
                "id": "SAL002",
                "name": "Jack Wilson",
                "role": "Senior Account Executive",
                "level": "senior",
                "email": "jack.wilson@company.com",
                "department": "sales",
            },
            {
                "id": "SAL003",
                "name": "Kelly Brown",
                "role": "Sales Development Rep",
                "level": "junior",
                "email": "kelly.brown@company.com",
                "department": "sales",
            },
            {
                "id": "SAL004",
                "name": "Leo Garcia",
                "role": "Regional Sales Director",
                "level": "staff",
                "email": "leo.garcia@company.com",
                "department": "sales",
            },
            {
                "id": "SAL005",
                "name": "Maya Patel",
                "role": "Account Executive",
                "level": "mid",
                "email": "maya.patel@company.com",
                "department": "sales",
            },
            {
                "id": "SAL006",
                "name": "Nathan Scott",
                "role": "VP of Sales",
                "level": "principal",
                "email": "nathan.scott@company.com",
                "department": "sales",
            },
        ],
        "marketing": [
            {
                "id": "MKT001",
                "name": "Olivia Thompson",
                "role": "Marketing Manager",
                "level": "senior",
                "email": "olivia.thompson@company.com",
                "department": "marketing",
            },
            {
                "id": "MKT002",
                "name": "Peter Anderson",
                "role": "Content Specialist",
                "level": "mid",
                "email": "peter.anderson@company.com",
                "department": "marketing",
            },
            {
                "id": "MKT003",
                "name": "Quinn Rodriguez",
                "role": "Marketing Coordinator",
                "level": "junior",
                "email": "quinn.rodriguez@company.com",
                "department": "marketing",
            },
            {
                "id": "MKT004",
                "name": "Rachel Lee",
                "role": "Director of Marketing",
                "level": "staff",
                "email": "rachel.lee@company.com",
                "department": "marketing",
            },
            {
                "id": "MKT005",
                "name": "Sam Miller",
                "role": "Social Media Manager",
                "level": "mid",
                "email": "sam.miller@company.com",
                "department": "marketing",
            },
        ],
    }

    if department not in teams:
        return json.dumps(
            {
                "error": f"Department '{department}' not found. Available departments: {', '.join(teams.keys())}"
            }
        )

    return json.dumps(teams[department], indent=2)


def get_expenses(employee_id: str, quarter: str) -> str:
    """특정 분기에 지정한 직원의 모든 지출 항목을 반환합니다.

    각 지출에는 날짜, category, 설명, 금액, 영수증 세부 사항, 승인 chain,
    판매자 정보 등 포괄적인 metadata가 포함됩니다. 직원은 분기당 몇 개부터
    150개 이상의 지출 항목을 가질 수 있으며, 각 항목에는 감사와 compliance를 위한
    상당한 metadata가 포함됩니다.

    Args:
        employee_id: 직원의 고유 식별자 (예: 'ENG001', 'SAL002')
        quarter: 분기 식별자 (예: 'Q1', 'Q2', 'Q3', 'Q4')

    Returns:
        다음 field를 가진 지출 object 배열의 JSON string:
        - expense_id: 지출의 고유 식별자
        - date: 지출 발생일의 ISO 형식 날짜
        - category: 지출 종류 (travel, meals, lodging, software, equipment 등)
        - description: 지출 세부 사항
        - amount: 달러 금액 (float)
        - currency: 통화 code (기본값 'USD')
        - status: 승인 상태 (approved, pending, rejected)
        - receipt_url: 업로드된 영수증 이미지 URL
        - approved_by: 승인한 manager 또는 재무 담당자
        - store_name: 판매자 또는 공급업체 이름
        - store_location: 판매자가 있는 도시와 주
        - reimbursement_date: 지출을 정산한 날짜 (해당하는 경우)
        - payment_method: 결제 방법 (corporate_card, personal_reimbursement)
        - project_code: Project 또는 cost center code
        - notes: 직원의 사유 또는 추가 context
    """

    time.sleep(DELAY_MULTIPLIER * 0.2)

    # employee_id 기반으로 deterministic하지만 다양한 지출 건수 생성
    random.seed(hash(employee_id + quarter))
    num_expenses = random.randint(
        EXPENSE_LINE_ITEMS_PER_PERSON_MIN, EXPENSE_LINE_ITEMS_PER_PERSON_MAX
    )

    # 분기 날짜 범위
    quarter_dates = {
        "Q1": (datetime(2024, 1, 1), datetime(2024, 3, 31)),
        "Q2": (datetime(2024, 4, 1), datetime(2024, 6, 30)),
        "Q3": (datetime(2024, 7, 1), datetime(2024, 9, 30)),
        "Q4": (datetime(2024, 10, 1), datetime(2024, 12, 31)),
    }

    if quarter.upper() not in quarter_dates:
        return json.dumps({"error": f"Invalid quarter '{quarter}'. Must be Q1, Q2, Q3, or Q4"})

    start_date, end_date = quarter_dates[quarter.upper()]

    # 지출 category와 일반적인 금액
    expense_categories = [
        ("travel", "Flight to client meeting", 400, 1500),
        ("travel", "Train ticket", 1000, 1500),
        ("travel", "Rental car", 1000, 1500),
        ("travel", "Taxi/Uber", 150, 200),
        ("travel", "Parking fee", 10, 50),
        ("lodging", "Hotel stay", 150, 1900),
        ("lodging", "Airbnb rental", 1000, 1950),
        ("meals", "Client dinner", 50, 250),
        ("meals", "Team lunch", 20, 100),
        ("meals", "Conference breakfast", 15, 40),
        ("meals", "Coffee meeting", 5, 25),
        ("software", "SaaS subscription", 10, 200),
        ("software", "API credits", 50, 500),
        ("equipment", "Monitor", 200, 800),
        ("equipment", "Keyboard", 50, 200),
        ("equipment", "Webcam", 50, 150),
        ("equipment", "Headphones", 100, 300),
        ("conference", "Conference ticket", 500, 2500),
        ("conference", "Workshop registration", 200, 1000),
        ("office", "Office supplies", 10, 100),
        ("office", "Books", 20, 80),
        ("internet", "Mobile data", 30, 100),
        ("internet", "WiFi hotspot", 20, 60),
    ]

    # 승인 담당 manager 이름
    managers = [
        "Sarah Johnson",
        "Michael Chen",
        "Emily Rodriguez",
        "David Park",
        "Jennifer Martinez",
    ]

    # Category별 상점/판매자 이름
    merchants = {
        "travel": [
            "United Airlines",
            "Delta",
            "American Airlines",
            "Southwest",
            "Enterprise Rent-A-Car",
        ],
        "lodging": ["Marriott", "Hilton", "Hyatt", "Airbnb", "Holiday Inn"],
        "meals": ["Olive Garden", "Starbucks", "The Capital Grille", "Chipotle", "Panera Bread"],
        "software": ["AWS", "GitHub", "Linear", "Notion", "Figma"],
        "equipment": ["Amazon", "Best Buy", "Apple Store", "B&H Photo", "Newegg"],
        "conference": ["EventBrite", "WWDC", "AWS re:Invent", "Google I/O", "ReactConf"],
        "office": ["Staples", "Office Depot", "Amazon", "Target"],
        "internet": ["Verizon", "AT&T", "T-Mobile", "Comcast"],
    }

    # 상점 위치용 미국 도시
    cities = [
        "San Francisco, CA",
        "New York, NY",
        "Austin, TX",
        "Seattle, WA",
        "Boston, MA",
        "Chicago, IL",
        "Denver, CO",
        "Los Angeles, CA",
        "Portland, OR",
        "Miami, FL",
    ]

    # Project code
    project_codes = [
        "PROJ-1001",
        "PROJ-1002",
        "PROJ-2001",
        "DEPT-ENG",
        "DEPT-OPS",
        "CLIENT-A",
        "CLIENT-B",
    ]

    # 사유 template
    justifications = {
        "travel": [
            "Client meeting to discuss Q4 roadmap and requirements",
            "On-site visit for infrastructure review and planning",
            "Conference attendance for professional development",
            "Team offsite for strategic planning session",
            "Customer presentation and product demo",
        ],
        "lodging": [
            "Hotel for multi-day client visit",
            "Accommodation during conference attendance",
            "Extended stay for project implementation",
            "Lodging for team collaboration week",
        ],
        "meals": [
            "Client dinner discussing partnership opportunities",
            "Team lunch during sprint planning",
            "Breakfast meeting with stakeholders",
            "Working dinner during crunch period",
        ],
        "software": [
            "Required tool for development workflow",
            "API credits for production workload",
            "Team collaboration platform subscription",
            "Design and prototyping tool license",
        ],
        "equipment": [
            "Replacing failed hardware",
            "Upgraded monitor for productivity",
            "Required for remote work setup",
            "Better equipment for video calls",
        ],
        "conference": [
            "Professional development - learning new technologies",
            "Networking with industry leaders and potential partners",
            "Presenting company work at industry event",
            "Training workshop for certification",
        ],
        "office": [
            "Supplies for home office setup",
            "Reference materials for project work",
            "Team whiteboarding supplies",
        ],
        "internet": [
            "Mobile hotspot for reliable connectivity",
            "Upgraded internet for remote work",
            "International data plan for travel",
        ],
    }

    expenses = []
    for i in range(num_expenses):
        category, desc_template, min_amt, max_amt = random.choice(expense_categories)

        # 분기 내 무작위 날짜 생성
        days_diff = (end_date - start_date).days
        random_days = random.randint(0, days_diff)
        expense_date = start_date + timedelta(days=random_days)

        # 금액 생성
        amount = round(random.uniform(min_amt, max_amt), 2)

        # 상태 (대부분 승인됨)
        status = random.choices(["approved", "pending", "rejected"], weights=[0.85, 0.10, 0.05])[0]

        # 추가 metadata 생성
        approved_by = random.choice(managers) if status == "approved" else None
        store_name = random.choice(merchants.get(category, ["Unknown Merchant"]))
        store_location = random.choice(cities)
        payment_method = random.choice(["corporate_card", "personal_reimbursement"])
        project_code = random.choice(project_codes)
        notes = random.choice(justifications.get(category, ["Business expense"]))

        # 승인된 지출의 reimbursement 날짜는 지출일 15–30일 후
        reimbursement_date = None
        if status == "approved" and payment_method == "personal_reimbursement":
            reimb_days = random.randint(15, 30)
            reimbursement_date = (expense_date + timedelta(days=reimb_days)).strftime("%Y-%m-%d")

        expenses.append(
            {
                "expense_id": f"{employee_id}_{quarter}_{i:03d}",
                "date": expense_date.strftime("%Y-%m-%d"),
                "category": category,
                "description": desc_template,
                "amount": amount,
                "currency": "USD",
                "status": status,
                "receipt_url": f"https://receipts.company.com/{employee_id}/{quarter}/{i:03d}.pdf",
                "approved_by": approved_by,
                "store_name": store_name,
                "store_location": store_location,
                "reimbursement_date": reimbursement_date,
                "payment_method": payment_method,
                "project_code": project_code,
                "notes": notes,
            }
        )

    # 날짜순 정렬
    expenses.sort(key=lambda x: x["date"])

    return json.dumps(expenses, indent=2)


def get_custom_budget(user_id: str) -> str:
    """특정 직원의 custom 분기별 출장 budget을 가져옵니다.

    대부분의 직원에게는 표준 $5,000 분기별 출장 budget이 있습니다. 하지만 일부
    직원은 role 요구에 따라 예외적인 custom budget을 가집니다.
    이 함수는 특정 직원에게 custom budget이 지정되었는지 확인합니다.

    Args:
        user_id: 직원의 고유 식별자 (예: 'ENG001', 'SAL002')

    Returns:
        다음 내용을 포함하는 JSON string:
        - user_id: 직원 식별자
        - has_custom_budget: Custom budget 존재 여부를 나타내는 boolean
        - travel_budget: 분기별 출장 budget 금액 (custom 또는 표준 $5,000)
        - reason: Custom budget에 대한 설명 (해당하는 경우)
        - currency: 통화 code (기본값 'USD')
    """
    time.sleep(DELAY_MULTIPLIER * 0.05)

    # 예외적 custom budget이 있는 직원
    custom_budgets = {
        "ENG002": {
            "user_id": "ENG002",
            "has_custom_budget": True,
            "travel_budget": 8000,
            "reason": "Staff engineer with regular client site visits",
            "currency": "USD",
        },
        "ENG004": {
            "user_id": "ENG004",
            "has_custom_budget": True,
            "travel_budget": 12000,
            "reason": "Principal engineer leading distributed team across multiple offices",
            "currency": "USD",
        },
        "SAL004": {
            "user_id": "SAL004",
            "has_custom_budget": True,
            "travel_budget": 15000,
            "reason": "Regional sales director covering west coast territory",
            "currency": "USD",
        },
        "SAL006": {
            "user_id": "SAL006",
            "has_custom_budget": True,
            "travel_budget": 20000,
            "reason": "VP of Sales with extensive client travel requirements",
            "currency": "USD",
        },
        "MKT004": {
            "user_id": "MKT004",
            "has_custom_budget": True,
            "travel_budget": 10000,
            "reason": "Director of Marketing attending industry conferences and partner meetings",
            "currency": "USD",
        },
    }

    # 사용자의 custom budget 확인
    if user_id in custom_budgets:
        return json.dumps(custom_budgets[user_id], indent=2)

    # 표준 budget 반환
    return json.dumps(
        {
            "user_id": user_id,
            "has_custom_budget": False,
            "travel_budget": 5000,
            "reason": "Standard quarterly travel budget",
            "currency": "USD",
        },
        indent=2,
    )


# 이용 가능한 모든 tool을 가져오는 helper 함수
def get_expense_tools():
    """Claude API에 사용할 모든 지출 관리 tool 목록을 반환합니다."""
    return [get_team_members, get_expenses, get_custom_budget]


if __name__ == "__main__":
    # Custom budget 확인을 보여주는 사용 예제
    print("=== Team Expense Analysis Example ===\n")

    # 팀 구성원 가져오기
    team = json.loads(get_team_members("engineering"))

    exceeded_standard = []
    for member in team[:5]:  # Demo에서는 처음 5명만 확인
        print(f"Checking expenses for {member['name']}...")

        # 이 사람의 지출 가져오기 (항목이 100개 이상일 수 있음)
        expenses = json.loads(get_expenses(member["id"], "Q3"))

        # 총 출장 지출 계산
        travel_total = sum(
            exp["amount"]
            for exp in expenses
            if exp["status"] == "approved" and exp["category"] in ["travel", "lodging"]
        )

        print(f"  - Found {len(expenses)} expense line items")
        print(f"  - Total approved travel expenses: ${travel_total:,.2f}")

        # 표준 $5,000 budget과 비교
        if travel_total > 5000:
            print("  ⚠️  Exceeded standard $5,000 budget")
            # 이제 예외적 custom budget이 있는지 확인
            custom = json.loads(get_custom_budget(member["id"]))
            print(f"  - Custom budget: ${custom['travel_budget']:,}")

            if travel_total > custom["travel_budget"]:
                print("  ❌ VIOLATION: Exceeded custom budget!")
                exceeded_standard.append(
                    {
                        "name": member["name"],
                        "spent": travel_total,
                        "custom_limit": custom["travel_budget"],
                    }
                )
            else:
                print("  ✅ Within custom budget limit")
        print()

    print("\n=== Summary: Employees Over Custom Budget ===")
    print(json.dumps(exceeded_standard, indent=2))
