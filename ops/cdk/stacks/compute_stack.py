"""ECS Fargate — deploy unit ① (API modular monolith) + ALB + RDS + Redis.

infra-design.md §6 (API compute) + U3 infrastructure-design (RDS/Redis/ALB)."""

from aws_cdk import (
    Duration,
    Fn,
    RemovalPolicy,
    Stack,
    aws_ec2 as ec2,
    aws_ecr as ecr,
    aws_ecs as ecs,
    aws_ecs_patterns as ecs_patterns,
    aws_elasticache as elasticache,
    aws_opensearchservice as opensearch,
    aws_rds as rds,
)
from constructs import Construct


class ComputeStack(Stack):
    def __init__(
        self,
        scope: Construct,
        construct_id: str,
        *,
        vpc: ec2.IVpc,
        opensearch_domain: opensearch.IDomain,
        **kwargs,
    ) -> None:
        super().__init__(scope, construct_id, **kwargs)

        # --- ECR repository (already created manually; import by name) ---
        self.api_repo = ecr.Repository.from_repository_name(self, "ApiRepo", "docsuri-api")

        # --- ECS cluster ---
        cluster = ecs.Cluster(self, "Cluster", cluster_name="docsuri", vpc=vpc)

        # --- RDS PostgreSQL (U3 spec: db.t4g.small Multi-AZ, 20 GB gp3) ---
        self.db = rds.DatabaseInstance(
            self, "Postgres",
            engine=rds.DatabaseInstanceEngine.postgres(version=rds.PostgresEngineVersion.VER_16),
            instance_type=ec2.InstanceType.of(ec2.InstanceClass.T4G, ec2.InstanceSize.SMALL),
            vpc=vpc,
            vpc_subnets=ec2.SubnetSelection(subnet_type=ec2.SubnetType.PRIVATE_ISOLATED),
            multi_az=True,
            allocated_storage=20,
            storage_type=rds.StorageType.GP3,
            backup_retention=Duration.days(7),
            deletion_protection=True,
            removal_policy=RemovalPolicy.RETAIN,
            credentials=rds.Credentials.from_generated_secret("docsuri_admin"),
            database_name="docsuri",
        )

        # --- ElastiCache Redis (U3 spec: cache.t4g.micro, 2-node Multi-AZ) ---
        redis_sg = ec2.SecurityGroup(self, "RedisSg", vpc=vpc, allow_all_outbound=False)
        isolated_subnets = vpc.select_subnets(subnet_type=ec2.SubnetType.PRIVATE_ISOLATED)
        redis_subnet_group = elasticache.CfnSubnetGroup(
            self, "RedisSubnetGroup",
            description="Redis isolated subnets",
            subnet_ids=isolated_subnets.subnet_ids,
        )
        self.redis = elasticache.CfnReplicationGroup(
            self, "Redis",
            replication_group_description="docsuri-session-store",
            engine="redis",
            engine_version="7.1",
            cache_node_type="cache.t4g.micro",
            num_cache_clusters=2,  # primary + replica (Multi-AZ)
            multi_az_enabled=True,
            automatic_failover_enabled=True,
            cache_subnet_group_name=redis_subnet_group.ref,
            security_group_ids=[redis_sg.security_group_id],
            at_rest_encryption_enabled=True,
            transit_encryption_enabled=True,
        )

        # --- Environment variables for the API container ---
        # DATABASE_URL is constructed from the RDS secret (username/password) + endpoint.
        # For initial deploy, use a SQLite fallback so the container boots + passes health
        # checks even before RDS is reachable (the app-shell gracefully handles this).
        # Production wiring reads from Secrets Manager at runtime — env var is the bootstrap.
        redis_endpoint = self.redis.attr_primary_end_point_address
        redis_port = self.redis.attr_primary_end_point_port

        container_env = {
            "ENV": "production",
            "DATABASE_URL": "sqlite:///tmp/docsuri-bootstrap.db",
            "REDIS_HOST": redis_endpoint,
            "REDIS_PORT": redis_port,
            "OPENSEARCH_ENDPOINT": Fn.join("", [
                "https://", opensearch_domain.domain_endpoint,
            ]),
        }

        # --- ALB + Fargate service (deploy unit ①: 0.25 vCPU / 512 MB, min 1 max 2) ---
        self.service = ecs_patterns.ApplicationLoadBalancedFargateService(
            self, "ApiService",
            cluster=cluster,
            service_name="docsuri-api",
            cpu=256,
            memory_limit_mib=512,
            desired_count=1,
            task_image_options=ecs_patterns.ApplicationLoadBalancedTaskImageOptions(
                image=ecs.ContainerImage.from_ecr_repository(self.api_repo, tag="latest"),
                container_port=8000,
                environment=container_env,
            ),
            assign_public_ip=True,  # NAT-free: public subnet + IGW outbound
            public_load_balancer=True,
            circuit_breaker=ecs.DeploymentCircuitBreaker(rollback=True),
            health_check_grace_period=Duration.seconds(60),
        )

        # ALB health check: the API serves no `GET /`, so the default `/` probe returns
        # 404 → target marked unhealthy → deployment circuit breaker rolls the stack back.
        # ponytail: /healthz is the cheap liveness route (no DB/Redis dep); use /readyz only
        # if you want readiness gating once downstream deps are wired.
        self.service.target_group.configure_health_check(path="/healthz")

        # Grant the task role permission to read the RDS secret (for runtime DB connection)
        if self.db.secret:
            self.db.secret.grant_read(self.service.task_definition.task_role)

        # Autoscaling: min 1 — max 2 (U3 spec)
        scaling = self.service.service.auto_scale_task_count(min_capacity=1, max_capacity=2)
        scaling.scale_on_cpu_utilization("CpuScale", target_utilization_percent=70)

        # SG: allow ECS → OpenSearch (HTTPS). Direction: egress from ECS → avoids cycle.
        self.service.service.connections.allow_to(
            opensearch_domain.connections, ec2.Port.tcp(443)
        )
        # SG: allow ECS → RDS
        self.db.connections.allow_from(
            self.service.service.connections, ec2.Port.tcp(5432)
        )
        # SG: allow ECS → Redis
        redis_sg.add_ingress_rule(
            self.service.service.connections.security_groups[0], ec2.Port.tcp(6379)
        )
