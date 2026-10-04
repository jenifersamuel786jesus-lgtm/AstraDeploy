from __future__ import annotations

import json
import os
import ssl
from collections.abc import Generator
from typing import Any

from sqlalchemy import create_engine
from sqlalchemy.engine import Engine, URL, make_url
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker


def normalize_database_url(raw: str) -> str:
    value = raw.strip()
    if value.startswith("mysql://"):
        return value.replace("mysql://", "mysql+pymysql://", 1)
    if value.startswith("postgres://"):
        return value.replace("postgres://", "postgresql+psycopg://", 1)
    if value.startswith("postgresql://") and "+" not in value.split(":", 1)[0]:
        return value.replace("postgresql://", "postgresql+psycopg://", 1)
    return value


def database_engine_parts(raw: str) -> tuple[URL, dict[str, Any]]:
    """Normalize managed URL TLS metadata into driver-native arguments in memory."""
    url = make_url(normalize_database_url(raw))
    connect_args: dict[str, Any] = {}
    if url.drivername == "mysql+pymysql":
        query = dict(url.query)
        ssl_value = query.pop("ssl", None)
        if ssl_value is not None:
            ssl_settings = _pymysql_ssl_settings(ssl_value)
            if ssl_settings is not None:
                connect_args["ssl"] = ssl_settings
            url = url.set(query=query)
    if url.drivername.startswith("sqlite"):
        connect_args["check_same_thread"] = False
    return url, connect_args


def _pymysql_ssl_settings(value: Any) -> dict[str, Any] | None:
    if isinstance(value, (tuple, list)):
        if len(value) != 1:
            raise ValueError("DATABASE_URL has an unsupported repeated MySQL ssl option.")
        value = value[0]
    source: dict[str, Any]
    if isinstance(value, dict):
        source: dict[str, Any] = dict(value)
    elif isinstance(value, bool):
        source = {"rejectUnauthorized": value}
    else:
        try:
            decoded = json.loads(str(value))
        except (TypeError, ValueError):
            label = str(value).strip().lower()
            if label in {"false", "no", "0", "off", "disabled"}:
                return None
            if label in {"true", "yes", "1", "on", "required", "require"}:
                source = {"rejectUnauthorized": True}
            else:
                raise ValueError("DATABASE_URL contains an unsupported MySQL ssl option format.") from None
        else:
            if decoded is False:
                return None
            if decoded is True:
                source = {"rejectUnauthorized": True}
            elif isinstance(decoded, dict):
                source = decoded
            else:
                raise ValueError("DATABASE_URL contains an unsupported MySQL ssl option format.")

    if "rejectUnauthorized" in source:
        reject_unauthorized = bool(source.pop("rejectUnauthorized"))
        source.setdefault("verify_mode", "required" if reject_unauthorized else "none")
        source.setdefault("check_hostname", reject_unauthorized)
    if "ciphers" in source and "cipher" not in source:
        source["cipher"] = source.pop("ciphers")
    if "minVersion" in source or "maxVersion" in source:
        # PyMySQL consumes an SSLContext; these Node TLS version keys have no direct dict mapping.
        source.pop("minVersion", None)
        source.pop("maxVersion", None)

    verify_mode = str(source.get("verify_mode", "required")).lower()
    if verify_mode not in {"none", "0", "false", "no"} and not source.get("ca") and not source.get("capath"):
        defaults = ssl.get_default_verify_paths()
        if defaults.cafile:
            source["ca"] = defaults.cafile
        elif defaults.capath:
            source["capath"] = defaults.capath
    return source


class Base(DeclarativeBase):
    pass


def configured_engine(raw: str, **engine_options: Any) -> Engine:
    url, managed_connect_args = database_engine_parts(raw)
    connect_args = dict(engine_options.pop("connect_args", {}))
    connect_args.update(managed_connect_args)
    engine_options.setdefault("pool_pre_ping", True)
    if connect_args:
        engine_options["connect_args"] = connect_args
    return create_engine(url, **engine_options)


DATABASE_URL = normalize_database_url(os.getenv("DATABASE_URL", "sqlite:///./astradeploy.db"))
engine = configured_engine(DATABASE_URL)
SessionLocal = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)


def get_db() -> Generator[Session, None, None]:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
