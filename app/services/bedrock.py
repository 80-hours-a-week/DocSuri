from __future__ import annotations

import boto3

from app.config import Settings


def build_bedrock_runtime_client(settings: Settings):
    session_kwargs = {}
    if settings.aws_profile:
        session_kwargs["profile_name"] = settings.aws_profile
    if settings.aws_region:
        session_kwargs["region_name"] = settings.aws_region
    session = boto3.Session(**session_kwargs)
    return session.client("bedrock-runtime")
