"""Batch Command API for High-Frequency Write Operations

POST /api/command/batch

Supports two modes:
- isolated (default): per-command transactions
- atomic: single transaction for all commands, events emitted only after commit
"""

from fastapi import HTTPException, Request
from typing import Dict, List, Tuple
from pydantic import BaseModel
from host.api_server import (
    app,
    rate_limit_check,
    get_client_ip,
    CreateInwardRequest,
    CreateTransferRequest,
)
from host.db_pool import db_pool


class BatchCommandItem(BaseModel):
    """Single command in a batch"""
    type: str  # "INWARD", "TRANSFER", "OUTWARD", "INVOICE"
    payload: Dict  # Command-specific payload


class BatchCommandRequest(BaseModel):
    """Batch command request"""
    commands: List[BatchCommandItem]
    mode: str = "isolated"  # "isolated" or "atomic"


async def _run_isolated_command(cmd: BatchCommandItem, request: Request, idx: int) -> Tuple[dict, bool]:
    """Execute a single command in isolated mode."""
    from host.command_endpoints import command_inward_commit, command_transfer_commit  # lazy import

    if cmd.type == "INWARD":
        inward_req = CreateInwardRequest(**cmd.payload)
        result = await command_inward_commit(inward_req, request)
        return {
            "command_index": idx,
            "command_type": "INWARD",
            "success": True,
            "event_id": result.get("event_id"),
            "document_id": result.get("document_id"),
            "affected_entities": result.get("affected_entities", []),
        }, True
    if cmd.type == "TRANSFER":
        transfer_req = CreateTransferRequest(**cmd.payload)
        result = await command_transfer_commit(transfer_req, request)
        return {
            "command_index": idx,
            "command_type": "TRANSFER",
            "success": True,
            "event_id": result.get("event_id"),
            "document_id": result.get("document_id"),
            "affected_entities": result.get("affected_entities", []),
        }, True

    return {
        "command_index": idx,
        "command_type": cmd.type,
        "success": False,
        "error": f"Unknown or unsupported command type: {cmd.type}",
    }, False


async def _run_atomic(batch_req: BatchCommandRequest, request: Request):
    """Execute all commands in one transaction and emit events after commit."""
    from host.command_endpoints import _process_inward, _process_transfer, _emit_events

    conn = None
    results = []
    successful = 0
    failed = 0
    events_to_emit: List[Tuple[str, str, int, Dict]] = []
    main_event_index_map: List[Tuple[int, int]] = []  # (result_idx, event_list_index)

    try:
        conn = db_pool.get_connection()
        if not conn:
            raise HTTPException(status_code=503, detail="Database unavailable")
        conn.autocommit = False

        for idx, cmd in enumerate(batch_req.commands):
            if cmd.type == "INWARD":
                inward_req = CreateInwardRequest(**cmd.payload)
                res = _process_inward(conn, inward_req)
                result_entry = {
                    "command_index": idx,
                    "command_type": "INWARD",
                    "success": True,
                    "document_id": res["document_id"],
                    "affected_entities": ["inward", "stock"],
                    "event_id": None,
                }
                results.append(result_entry)
                main_event_index_map.append((len(results) - 1, len(events_to_emit)))
                events_to_emit.extend([res["main_event"], *res["stock_events"]])
                successful += 1
            elif cmd.type == "TRANSFER":
                transfer_req = CreateTransferRequest(**cmd.payload)
                res = _process_transfer(conn, transfer_req)
                result_entry = {
                    "command_index": idx,
                    "command_type": "TRANSFER",
                    "success": True,
                    "document_id": res["document_id"],
                    "affected_entities": ["transfer", "stock"],
                    "event_id": None,
                }
                results.append(result_entry)
                main_event_index_map.append((len(results) - 1, len(events_to_emit)))
                events_to_emit.extend([res["main_event"], *res["stock_events"]])
                successful += 1
            else:
                results.append({
                    "command_index": idx,
                    "command_type": cmd.type,
                    "success": False,
                    "error": f"Unknown or unsupported command type: {cmd.type}",
                })
                failed += 1

        # Commit once for all
        conn.commit()

        # Emit events after commit
        event_ids = await _emit_events(events_to_emit)
        for res_idx, event_list_idx in main_event_index_map:
            if event_list_idx < len(event_ids):
                results[res_idx]["event_id"] = event_ids[event_list_idx]

        return {
            "success": failed == 0,
            "results": results,
            "total_commands": len(batch_req.commands),
            "successful": successful,
            "failed": failed,
        }
    except HTTPException as e:
        if conn:
            conn.rollback()
        raise e
    except Exception as e:
        if conn:
            conn.rollback()
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")
    finally:
        if conn:
            conn.autocommit = True
            db_pool.return_connection(conn)


@app.post("/api/command/batch")
async def command_batch(batch_req: BatchCommandRequest, request: Request):
    """
    Execute multiple commands in a batch.

    Modes:
    - isolated (default): per-command transaction
    - atomic: single transaction, events emitted after commit
    """
    client_ip = get_client_ip(request)
    if not rate_limit_check(client_ip):
        raise HTTPException(status_code=429, detail="Rate limit exceeded")

    if not batch_req.commands:
        raise HTTPException(status_code=400, detail="No commands provided")
    if len(batch_req.commands) > 50:
        raise HTTPException(status_code=400, detail="Maximum 50 commands per batch")
    if batch_req.mode not in ("isolated", "atomic"):
        raise HTTPException(status_code=400, detail="Invalid mode. Use 'isolated' or 'atomic'")

    if batch_req.mode == "atomic":
        return await _run_atomic(batch_req, request)

    # isolated mode
    results = []
    successful = 0
    failed = 0

    for idx, cmd in enumerate(batch_req.commands):
        try:
            result, ok = await _run_isolated_command(cmd, request, idx)
            results.append(result)
            if ok:
                successful += 1
            else:
                failed += 1
        except HTTPException as e:
            results.append({
                "command_index": idx,
                "command_type": cmd.type,
                "success": False,
                "error": e.detail,
                "status_code": e.status_code,
            })
            failed += 1
        except Exception as e:
            results.append({
                "command_index": idx,
                "command_type": cmd.type,
                "success": False,
                "error": str(e),
            })
            failed += 1

    return {
        "success": failed == 0,
        "results": results,
        "total_commands": len(batch_req.commands),
        "successful": successful,
        "failed": failed,
    }

