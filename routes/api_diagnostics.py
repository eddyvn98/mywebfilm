from flask import Blueprint, jsonify, request

from runtime_db import list_incomplete_operations

diagnostics_bp = Blueprint("api_diagnostics", __name__)


@diagnostics_bp.route("/api/diagnostics/operations")
def incomplete_operations():
    try:
        limit = int(request.args.get("limit", "50"))
    except ValueError:
        limit = 50
    return jsonify({
        "status": "ok",
        "operations": list_incomplete_operations(limit),
    })
