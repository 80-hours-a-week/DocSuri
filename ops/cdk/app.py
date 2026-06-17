#!/usr/bin/env python3
"""DocSuri CDK app — provisions the system-wide infrastructure defined in
aidlc-docs/construction/infrastructure-design/infrastructure-design.md.

Usage:
    cd ops/cdk && cdk synth   # synthesize CloudFormation
    cd ops/cdk && cdk deploy  # provision to AWS (ap-northeast-2)

Stacks are split by lifecycle/blast-radius so a network change doesn't redeploy compute."""

import aws_cdk as cdk
from stacks.compute_stack import ComputeStack
from stacks.frontend_stack import FrontendStack
from stacks.ingestion_stack import IngestionStack
from stacks.network_stack import NetworkStack
from stacks.search_stack import SearchStack

app = cdk.App()

env = cdk.Environment(account="028317349537", region="ap-northeast-2")

network = NetworkStack(app, "Docsuri-Network", env=env)
search = SearchStack(app, "Docsuri-Search", vpc=network.vpc, env=env)
compute = ComputeStack(
    app, "Docsuri-Compute",
    vpc=network.vpc,
    opensearch_domain=search.domain,
    env=env,
)
ingestion = IngestionStack(
    app, "Docsuri-Ingestion",
    vpc=network.vpc,
    opensearch_domain=search.domain,
    env=env,
)
# Deploy unit ④ — U5 frontend. The BFF (server-side) calls the backend gateway over its
# CloudFront HTTPS URL (which injects the origin-auth secret on the way to the backend ALB).
frontend = FrontendStack(
    app, "Docsuri-Frontend",
    vpc=network.vpc,
    gateway_url=f"https://{compute.cdn.distribution_domain_name}",
    env=env,
)

app.synth()
