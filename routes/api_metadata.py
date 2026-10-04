from flask import Blueprint, jsonify

from metadata_job_store import metadata_job_counts
from metadata_worker import enqueue_catalog_items

metadata_bp = Blueprint("api_metadata", __name__)


@metadata_bp.route("/api/metadata/status")
def metadata_status():
    return jsonify({
        "status": "ok",
        "jobs": metadata_job_counts(),
    })


@metadata_bp.route("/api/metadata/enqueue", methods=["POST"])
def metadata_enqueue():
    queued = enqueue_catalog_items()
    return jsonify({
        "status": "ok",
        "queued": queued,
        "jobs": metadata_job_counts(),
    }), 202
