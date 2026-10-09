"""
SQL injection 취약점이 있는 SQL query builder.
SQL query의 위험한 string formatting을 시연합니다.
"""


class UserDatabase:
    """간단한 database interface(mock)."""

    def execute(self, query: str) -> list[dict]:
        """Mock 실행 - 검토를 위해 query만 반환합니다."""
        print(f"Executing: {query}")
        return []


class QueryBuilder:
    """사용자 작업에 대한 SQL query를 만듭니다."""

    def __init__(self, db: UserDatabase):
        self.db = db

    def get_user_by_name(self, username: str) -> dict | None:
        """
        Username으로 사용자를 가져옵니다.

        BUG: SQL INJECTION 취약점!
        User input에 string formatting을 사용하면 SQL injection이 가능합니다.
        """
        # 위험: User input과 f-string이나 % formatting을 절대 사용하지 마세요!
        query = f"SELECT * FROM users WHERE username = '{username}'"
        results = self.db.execute(query)
        return results[0] if results else None

    def get_user_by_name_safe(self, username: str) -> dict | None:
        """Parameterized query를 사용하는 안전한 버전."""
        # Parameterized query 사용(개념을 보여주는 pseudo-code)
        query = "SELECT * FROM users WHERE username = ?"
        # 실제 코드: self.db.execute(query, (username,))
        print(f"Safe query with parameter: {query}, params: ({username},)")
        return None

    def search_users(self, search_term: str, limit: int = 10) -> list[dict]:
        """
        Term으로 사용자를 검색합니다.

        BUG: LIKE 절을 통한 SQL INJECTION!
        """
        # 위험: User input을 LIKE 절에 직접 사용
        query = f"SELECT * FROM users WHERE name LIKE '%{search_term}%' LIMIT {limit}"
        return self.db.execute(query)

    def delete_user(self, user_id: str) -> bool:
        """
        사용자를 삭제합니다.

        BUG: DELETE statement의 SQL INJECTION!
        이는 데이터 손실을 일으킬 수 있어 특히 위험합니다.
        """
        # 위험: DELETE에 검증되지 않은 user input 사용
        query = f"DELETE FROM users WHERE id = {user_id}"
        self.db.execute(query)
        return True

    def get_users_by_role(self, role: str, order_by: str = "name") -> list[dict]:
        """
        역할별 사용자를 가져옵니다.

        BUG: ORDER BY 절의 SQL INJECTION!
        ORDER BY 절도 악용될 수 있습니다.
        """
        # 위험: 사용자가 제어하는 ORDER BY
        query = f"SELECT * FROM users WHERE role = '{role}' ORDER BY {order_by}"
        return self.db.execute(query)


if __name__ == "__main__":
    db = UserDatabase()
    qb = QueryBuilder(db)

    print("=== Demonstrating SQL Injection Vulnerabilities ===\n")

    # 예제 1: 기본 injection
    print("1. Basic username injection:")
    qb.get_user_by_name("admin' OR '1'='1")
    # 실행: SELECT * FROM users WHERE username = 'admin' OR '1'='1'
    # 모든 사용자를 반환합니다!

    print("\n2. Search term injection:")
    qb.search_users("test%' OR 1=1--")
    # LIKE를 우회하여 모두 반환할 수 있습니다

    print("\n3. DELETE injection:")
    qb.delete_user("1 OR 1=1")
    # 실행: DELETE FROM users WHERE id = 1 OR 1=1
    # 모든 사용자를 삭제합니다!

    print("\n4. ORDER BY injection:")
    qb.get_users_by_role("admin", "name; DROP TABLE users--")
    # 임의의 SQL 명령을 실행할 수 있습니다!

    print("\n=== Safe Version ===")
    qb.get_user_by_name_safe("admin' OR '1'='1")
    # Parameter가 올바르게 escape됩니다
