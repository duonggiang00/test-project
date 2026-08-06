import argparse
import os
from dataclasses import dataclass

import psycopg2
from psycopg2 import sql
from psycopg2.extensions import connection as PsycopgConnection
from sqlalchemy.engine import URL, make_url

from app.core.config import settings


LOCAL_TEST_HOSTS = {"127.0.0.1", "localhost", "::1"}


@dataclass(frozen=True)
class TestDatabaseTarget:
    base: URL
    target: URL
    admin_database: str


def validate_test_database_target(
    base_database_url: str,
    test_database_url: str,
    admin_database: str = "postgres",
) -> TestDatabaseTarget:
    base = make_url(base_database_url)
    target = make_url(test_database_url)

    if not base.drivername.startswith("postgresql"):
        raise ValueError("The base database must use PostgreSQL")
    if not target.drivername.startswith("postgresql"):
        raise ValueError("The test database must use PostgreSQL")
    if base.host not in LOCAL_TEST_HOSTS or target.host not in LOCAL_TEST_HOSTS:
        raise ValueError("The integration runner only manages local PostgreSQL hosts")
    if (base.port or 5432) != (target.port or 5432):
        raise ValueError("The test database must use the same local server as the base URL")
    if not base.database or not target.database:
        raise ValueError("Both database URLs must include database names")
    if target.database == base.database:
        raise ValueError("The test database must differ from the development database")
    if target.database == admin_database:
        raise ValueError("The test database must differ from the admin database")
    if not target.database.endswith("_test"):
        raise ValueError("The managed database name must end with _test")

    return TestDatabaseTarget(base=base, target=target, admin_database=admin_database)


class TestDatabaseManager:
    def __init__(self, target: TestDatabaseTarget):
        self.target = target
        self.created_by_manager = False

    def _connect_admin(self) -> PsycopgConnection:
        return self._connect(self.target.admin_database)

    def _connect(self, database: str) -> PsycopgConnection:
        return psycopg2.connect(
            dbname=database,
            user=self.target.target.username,
            password=self.target.target.password,
            host=self.target.target.host,
            port=self.target.target.port,
        )

    def exists(self) -> bool:
        connection = self._connect_admin()
        try:
            connection.autocommit = True
            with connection.cursor() as cursor:
                cursor.execute(
                    "SELECT 1 FROM pg_database WHERE datname = %s",
                    (self.target.target.database,),
                )
                return cursor.fetchone() is not None
        finally:
            connection.close()

    def connect_target(self) -> PsycopgConnection:
        target_database = self.target.target.database
        assert target_database is not None
        return self._connect(target_database)

    def create(self) -> None:
        connection = self._connect_admin()
        try:
            connection.autocommit = True
            with connection.cursor() as cursor:
                cursor.execute(
                    "SELECT 1 FROM pg_database WHERE datname = %s",
                    (self.target.target.database,),
                )
                if cursor.fetchone() is not None:
                    raise RuntimeError(
                        "Refusing to reuse a pre-existing test database; "
                        "inspect it and run the explicit guarded drop command first"
                    )
                cursor.execute(
                    sql.SQL("CREATE DATABASE {}").format(
                        sql.Identifier(self.target.target.database)
                    )
                )
            self.created_by_manager = True
        finally:
            connection.close()

        try:
            target_database = self.target.target.database
            assert target_database is not None
            target_connection = self._connect(target_database)
            try:
                target_connection.autocommit = True
                with target_connection.cursor() as cursor:
                    cursor.execute(
                        "SELECT 1 FROM pg_available_extensions WHERE name = %s",
                        ("vector",),
                    )
                    if cursor.fetchone() is not None:
                        cursor.execute("CREATE EXTENSION IF NOT EXISTS vector")
                        print("TEST_DATABASE_EXTENSION_ENABLED name=vector", flush=True)
                    else:
                        print(
                            "TEST_DATABASE_EXTENSION_SKIPPED "
                            "name=vector reason=not-installed-on-server",
                            flush=True,
                        )
            finally:
                target_connection.close()
        except Exception:
            self.drop_created()
            raise

        self._print_event("CREATED")

    def drop_created(self) -> None:
        if not self.created_by_manager:
            return
        self._drop()
        self.created_by_manager = False

    def drop_explicit(self) -> None:
        self._drop()

    def _drop(self) -> None:
        connection = self._connect_admin()
        try:
            connection.autocommit = True
            with connection.cursor() as cursor:
                cursor.execute(
                    """
                    SELECT pg_terminate_backend(pid)
                    FROM pg_stat_activity
                    WHERE datname = %s AND pid <> pg_backend_pid()
                    """,
                    (self.target.target.database,),
                )
                cursor.execute(
                    sql.SQL("DROP DATABASE IF EXISTS {}").format(
                        sql.Identifier(self.target.target.database)
                    )
                )
        finally:
            connection.close()

        self._print_event("DROPPED")

    def _print_event(self, action: str) -> None:
        print(
            f"TEST_DATABASE_{action} "
            f"host={self.target.target.host} "
            f"port={self.target.target.port or 5432} "
            f"database={self.target.target.database}",
            flush=True,
        )


def build_manager() -> TestDatabaseManager:
    admin_database = os.getenv("POSTGRES_ADMIN_DATABASE", "postgres")
    target = validate_test_database_target(
        settings.BASE_DATABASE_URL,
        settings.ISOLATED_TEST_DATABASE_URL,
        admin_database,
    )
    return TestDatabaseManager(target)


def main() -> int:
    parser = argparse.ArgumentParser(description="Manage the guarded local test database")
    parser.add_argument("action", choices=("status", "create", "drop"))
    args = parser.parse_args()

    manager = build_manager()
    if args.action == "status":
        state = "exists" if manager.exists() else "absent"
        print(
            "TEST_DATABASE_STATUS "
            f"host={manager.target.target.host} "
            f"port={manager.target.target.port or 5432} "
            f"database={manager.target.target.database} state={state}",
            flush=True,
        )
    elif args.action == "create":
        manager.create()
    else:
        manager.drop_explicit()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
