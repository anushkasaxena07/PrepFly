"""
PrepFly Tenancy Enforcement Service
Provides server-derived tenant isolation, TenantContext management,
and safe multi-tenant scoping primitives.
"""

from dataclasses import dataclass
from typing import Optional, Any, Dict
from flask import g, request, jsonify, Response
import functools
import re

import logging

logger = logging.getLogger("prepfly.tenancy")

@dataclass(frozen=True)
class TenantContext:
    user_id: str
    role: str
    org_id: Optional[str]
    is_super_admin: bool = False
    is_org_admin: bool = False
    is_student: bool = False
    membership_status: Optional[str] = None

    def can_access_tenant(self, target_org_id: Optional[str]) -> bool:
        """
        Determines whether the current context is authorized to access resources
        belonging to target_org_id.
        """
        if self.is_super_admin:
            return True
        if not self.org_id or not target_org_id:
            return False
        return self.org_id == target_org_id


def build_tenant_context(user_payload: Dict[str, Any], db_client=None) -> Optional[TenantContext]:
    """
    Derives TenantContext strictly from authenticated server-side user data.
    Never trusts client headers (e.g. X-Organization-Id) for scoping.
    """
    if not user_payload:
        return None

    user_id = str(user_payload.get("sub") or user_payload.get("id") or "")
    role = str(user_payload.get("role") or "").strip().upper()
    email = str(user_payload.get("email") or "").strip().lower()
    
    super_admin_emails = {
        "saxenaanushka9645@gmail.com",
        "superadmin@prepfly.io",
        "owner@prepfly.io",
        "superadmin@interviewai.io",
        "owner@interviewai.io"
    }

    is_super_admin = role in ("SUPER_ADMIN", "SUPERADMIN", "SUPER ADMIN") or email in super_admin_emails
    is_org_admin = role in ("ORGANIZATION ADMIN", "ADMIN")
    is_student = not is_super_admin and not is_org_admin

    # For Super Admin: may optionally impersonate/scope via query arg if explicitly requested
    if is_super_admin:
        requested_org = request.args.get("organization_id") or request.args.get("org_id")
        if requested_org and re.match(r"^[a-zA-Z0-9_\-]+$", requested_org):
            scoped_org = requested_org
        else:
            scoped_org = user_payload.get("organization_id")
        return TenantContext(
            user_id=user_id,
            role="SUPER_ADMIN",
            org_id=scoped_org,
            is_super_admin=True,
            is_org_admin=True,
            is_student=False,
            membership_status="active"
        )

    # For Organization Admin: derive org_id strictly from user token / DB record
    org_id = user_payload.get("organization_id")
    membership_status = "active"

    # If org_id is not in token and db_client is provided, query admin / org_memberships table
    if not org_id and db_client and user_id:
        try:
            mem_res = db_client.table("org_memberships").select("*").eq("user_id", user_id).eq("status", "active").execute()
            if mem_res and hasattr(mem_res, "data") and mem_res.data:
                org_id = mem_res.data[0].get("organization_id")
                membership_status = mem_res.data[0].get("status")
        except Exception as err:
            logger.debug("Failed to query org_memberships in build_tenant_context: %s", err)

        if not org_id and is_org_admin:
            try:
                adm_res = db_client.table("admin").select("organization_id").eq("id", user_id).execute()
                if adm_res and hasattr(adm_res, "data") and adm_res.data:
                    org_id = adm_res.data[0].get("organization_id")
            except Exception as err:
                logger.debug("Failed to query admin table in build_tenant_context: %s", err)

    return TenantContext(
        user_id=user_id,
        role=role,
        org_id=org_id,
        is_super_admin=is_super_admin,
        is_org_admin=is_org_admin,
        is_student=is_student,
        membership_status=membership_status
    )


def get_current_tenant_context() -> Optional[TenantContext]:
    """Retrieves current TenantContext from flask.g."""
    return getattr(g, "tenant_context", None)


def tenant_not_found(resource_name: str = "Resource"):
    """
    Standard Golden Rule 4 response: returns HTTP 404 instead of 403
    when accessing a foreign or missing resource, preventing cross-tenant probing.
    """
    return jsonify({"error": f"{resource_name} not found"}), 404


def get_org_seat_status(org_id: str, db_client) -> Dict[str, Any]:
    """
    Calculates institutional seat entitlement and capacity.
    """
    max_seats = 100
    try:
        org_res = db_client.table("organization").select("max_seats").eq("id", org_id).execute()
        if org_res and org_res.data and len(org_res.data) > 0:
            max_seats = int(org_res.data[0].get("max_seats") or 100)
    except Exception as err:
        logger.debug("Failed to query organization max_seats: %s", err)

    active_user_ids = set()
    try:
        mem_res = db_client.table("org_memberships").select("user_id").eq("organization_id", org_id).eq("status", "active").execute()
        if mem_res and mem_res.data:
            for m in mem_res.data:
                if m.get("user_id"):
                    active_user_ids.add(str(m["user_id"]))
    except Exception as err:
        logger.debug("Failed to query org_memberships active seats: %s", err)

    try:
        std_res = db_client.table("students").select("id").eq("organization_id", org_id).neq("status", "Archived").execute()
        if std_res and std_res.data:
            for s in std_res.data:
                if s.get("id"):
                    active_user_ids.add(str(s["id"]))
    except Exception as err:
        logger.debug("Failed to query students active seats: %s", err)

    current_seats = len(active_user_ids)
    remaining_seats = max(0, max_seats - current_seats)
    return {
        "max_seats": max_seats,
        "current_seats": current_seats,
        "remaining_seats": remaining_seats,
        "is_full": current_seats >= max_seats
    }


def parse_student_csv_data(csv_text: str):
    """
    Parses and validates CSV text containing student roster rows.
    Returns (valid_rows, invalid_rows).
    """
    import csv
    import io

    valid_rows = []
    invalid_rows = []
    seen_emails = set()

    email_regex = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")

    reader = csv.reader(io.StringIO(csv_text.strip()))
    header = None

    for row_idx, row in enumerate(reader, start=1):
        if not row or not any(row):
            continue
        cleaned_row = [c.strip() for c in row]
        if header is None:
            # Check if this row is a header
            first_val = cleaned_row[0].lower()
            if "name" in first_val or "email" in first_val or "roll" in first_val:
                header = [c.lower().replace(" ", "_") for c in cleaned_row]
                continue
            else:
                header = ["name", "email", "roll_number", "department", "year"]

        row_dict = {}
        for col_idx, col_name in enumerate(header):
            val = cleaned_row[col_idx] if col_idx < len(cleaned_row) else ""
            row_dict[col_name] = val

        name = row_dict.get("name") or row_dict.get("student_name") or ""
        email = (row_dict.get("email") or row_dict.get("student_email") or "").lower()
        roll = row_dict.get("roll_number") or row_dict.get("roll") or ""
        dept = row_dict.get("department") or row_dict.get("branch") or "General"
        year = row_dict.get("year") or "2026"

        if not name:
            invalid_rows.append({"row": row_idx, "email": email, "reason": "Missing student name"})
            continue

        if not email or not email_regex.match(email):
            invalid_rows.append({"row": row_idx, "name": name, "email": email, "reason": "Invalid or missing email format"})
            continue

        if email in seen_emails:
            invalid_rows.append({"row": row_idx, "name": name, "email": email, "reason": "Duplicate email in CSV"})
            continue

        seen_emails.add(email)
        valid_rows.append({
            "name": name,
            "email": email,
            "roll_number": roll,
            "department": dept,
            "year": year
        })

    return valid_rows, invalid_rows


def link_student_to_college(user_id: str, org_id: str, db_client, roll_number: str = "", department: str = "") -> bool:
    """
    Links a student to an organization.
    Enforces Single Active College Membership by archiving any prior active memberships.
    """
    from datetime import datetime, timezone
    now_iso = datetime.now(timezone.utc).isoformat()

    # 1. Archive prior memberships
    try:
        db_client.table("org_memberships").update({
            "status": "archived",
            "updated_at": now_iso
        }).eq("user_id", user_id).eq("status", "active").execute()
    except Exception as err:
        logger.debug("Failed to archive prior memberships: %s", err)

    # 2. Upsert active membership for target organization
    mem_id = f"mem_{user_id}_{org_id}"[:36]
    try:
        db_client.table("org_memberships").upsert({
            "id": mem_id,
            "organization_id": org_id,
            "user_id": user_id,
            "role": "student",
            "status": "active",
            "roll_number": roll_number,
            "department": department or "General",
            "joined_at": now_iso,
            "updated_at": now_iso
        }).execute()
    except Exception as err:
        logger.debug("Failed to upsert org_membership: %s", err)
        return False

    # 3. Update users table organization_id
    try:
        db_client.table("users").update({"organization_id": org_id}).eq("id", user_id).execute()
    except Exception as err:
        logger.debug("Failed to update users organization_id: %s", err)

    return True


def unlink_student_from_college(user_id: str, org_id: str, db_client) -> bool:
    """
    Unlinks a student from an organization.
    Archives membership, reverts users.organization_id to NULL, and marks students roster Archived.
    Preserves historical test and interview records.
    """
    from datetime import datetime, timezone
    now_iso = datetime.now(timezone.utc).isoformat()

    # 1. Archive active membership
    try:
        db_client.table("org_memberships").update({
            "status": "archived",
            "updated_at": now_iso
        }).eq("organization_id", org_id).eq("user_id", user_id).execute()
    except Exception as err:
        logger.debug("Failed to archive org_memberships during unlink: %s", err)

    # 2. Revert user account to independent
    try:
        db_client.table("users").update({"organization_id": None}).eq("id", user_id).execute()
    except Exception as err:
        logger.debug("Failed to clear users organization_id during unlink: %s", err)

    # 3. Mark students roster row as Archived
    try:
        db_client.table("students").update({"status": "Archived"}).eq("organization_id", org_id).eq("id", user_id).execute()
    except Exception as err:
        logger.debug("Failed to archive students row during unlink: %s", err)

    return True
