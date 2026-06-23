"""ECS Fargate — deploy unit ② (ingestion worker) + SQS + EventBridge schedule.

infra-design.md §2 (worker) + §3 (EventBridge) + §4 (S3)."""

from aws_cdk import (
    Duration,
    Fn,
    RemovalPolicy,
    Stack,
)
from aws_cdk import (
    aws_ec2 as ec2,
)
from aws_cdk import (
    aws_ecr as ecr,
)
from aws_cdk import (
    aws_ecs as ecs,
)
from aws_cdk import (
    aws_events as events,
)
from aws_cdk import (
    aws_events_targets as targets,
)
from aws_cdk import (
    aws_iam as iam,
)
from aws_cdk import (
    aws_opensearchservice as opensearch,
)
from aws_cdk import (
    aws_rds as rds,
)
from aws_cdk import (
    aws_s3 as s3,
)
from aws_cdk import (
    aws_sqs as sqs,
)
from constructs import Construct

# Bedrock text-embedding model for the worker (Cohere Embed multilingual, 1024-dim —
# matches the discovery/search side). Region-scoped ARN built from this id below.
_BEDROCK_MODEL_ID = "cohere.embed-multilingual-v3"


class IngestionStack(Stack):
    def __init__(
        self,
        scope: Construct,
        construct_id: str,
        *,
        vpc: ec2.IVpc,
        opensearch_domain: opensearch.IDomain,
        database: rds.IDatabaseInstance,
        **kwargs,
    ) -> None:
        super().__init__(scope, construct_id, **kwargs)

        # --- ECR (already created manually; import by name) ---
        self.repo = ecr.Repository.from_repository_name(self, "IngestionRepo", "docsuri-ingestion")

        # --- SQS: ingestion queue + DLQ (infra-design §2.3) ---
        dlq = sqs.Queue(
            self, "IngestionDlq",
            queue_name="docsuri-ingestion-dlq",
            retention_period=Duration.days(14),
            encryption=sqs.QueueEncryption.SQS_MANAGED,
        )
        self.queue = sqs.Queue(
            self, "IngestionQueue",
            queue_name="docsuri-ingestion-queue",
            visibility_timeout=Duration.seconds(300),
            retention_period=Duration.days(14),
            encryption=sqs.QueueEncryption.SQS_MANAGED,
            dead_letter_queue=sqs.DeadLetterQueue(max_receive_count=3, queue=dlq),
        )

        # --- S3: full-text storage (infra-design §4) ---
        self.bucket = s3.Bucket(
            self, "FulltextBucket",
            bucket_name=f"docsuri-papers-fulltext-{Stack.of(self).account}",
            versioned=True,
            encryption=s3.BucketEncryption.S3_MANAGED,
            intelligent_tiering_configurations=[
                s3.IntelligentTieringConfiguration(
                    name="archive-cold",
                    archive_access_tier_time=Duration.days(180),
                    deep_archive_access_tier_time=Duration.days(365),
                ),
            ],
            removal_policy=RemovalPolicy.RETAIN,
        )

        # --- EventBridge: daily arXiv schedule (infra-design §3.1) ---
        events.Rule(
            self, "ArxivDailySchedule",
            rule_name="docsuri-arxiv-daily",
            schedule=events.Schedule.cron(hour="6", minute="0"),  # 06:00 UTC = 15:00 KST
            targets=[
                targets.SqsQueue(
                    self.queue, message=events.RuleTargetInput.from_text("on_schedule_tick")
                )
            ],
        )

        # --- ECS Fargate: ingestion worker (0.5 vCPU / 1 GB, SQS polling) ---
        cluster = ecs.Cluster.from_cluster_attributes(
            self, "Cluster", cluster_name="docsuri", vpc=vpc,
            security_groups=[],
        )
        task_def = ecs.FargateTaskDefinition(
            self, "WorkerTaskDef",
            cpu=512,
            memory_limit_mib=1024,
        )

        # Control-plane DSN WITHOUT the password — libpq reads PGPASSWORD (injected as a secret
        # below) for any field absent from the conninfo. Keeps the DB credential out of the
        # plaintext task-def env, mirroring how the API injects DB_PASSWORD.
        control_plane_dsn = Fn.join("", [
            "postgresql://docsuri_admin@",
            database.db_instance_endpoint_address,
            ":",
            database.db_instance_endpoint_port,
            "/docsuri",
        ])
        assert database.secret is not None  # from_generated_secret always creates one

        task_def.add_container(
            "worker",
            image=ecs.ContainerImage.from_ecr_repository(self.repo, tag="latest"),
            logging=ecs.LogDrivers.aws_logs(stream_prefix="ingestion"),
            environment={
                "DOCSURI_ENV": "production",
                "DOCSURI_AWS_REGION": self.region,
                "DOCSURI_S3_BUCKET": self.bucket.bucket_name,
                "DOCSURI_BEDROCK_MODEL_ID": _BEDROCK_MODEL_ID,
                "DOCSURI_OPENSEARCH_ENDPOINT": f"https://{opensearch_domain.domain_endpoint}",
                "DOCSURI_OPENSEARCH_INDEX": "docsuri-corpus-v1",
                "DOCSURI_CONTROL_PLANE_DSN": control_plane_dsn,
                "DOCSURI_SQS_QUEUE_URL": self.queue.queue_url,
                "DOCSURI_SQS_DLQ_URL": dlq.queue_url,
                # FR-17 multimodal figure/table assets ON (Pillow/pypdfium2/pdfplumber baked
                # into the image via the [assets] extra).
                "DOCSURI_MULTIMODAL_ASSETS_ENABLED": "true",
            },
            secrets={
                "PGPASSWORD": ecs.Secret.from_secrets_manager(database.secret, "password"),
            },
        )

        self.service = ecs.FargateService(
            self, "WorkerService",
            service_name="docsuri-ingestion",
            cluster=cluster,
            task_definition=task_def,
            desired_count=0,  # scale-to-zero at rest
            assign_public_ip=True,  # NAT-free: public subnet + IGW
            circuit_breaker=ecs.DeploymentCircuitBreaker(rollback=True),
            vpc_subnets=ec2.SubnetSelection(subnet_type=ec2.SubnetType.PUBLIC),
        )

        # Autoscaling: min 0 — max 3 (SQS-driven step scaling)
        from aws_cdk import aws_applicationautoscaling as appscaling

        scaling = self.service.auto_scale_task_count(min_capacity=0, max_capacity=3)
        scaling.scale_on_metric(
            "SqsDepth",
            metric=self.queue.metric_approximate_number_of_messages_visible(),
            scaling_steps=[
                appscaling.ScalingInterval(upper=0, change=0),
                appscaling.ScalingInterval(lower=10, change=1),
                appscaling.ScalingInterval(lower=50, change=2),
            ],
            adjustment_type=appscaling.AdjustmentType.CHANGE_IN_CAPACITY,
        )

        # SG: worker → OpenSearch (HTTPS) + RDS (Postgres). Add egress on the worker side rather
        # than ingress on the other stack (avoids a cross-stack dependency cycle).
        self.service.connections.allow_to(opensearch_domain.connections, ec2.Port.tcp(443))
        self.service.connections.allow_to(database.connections, ec2.Port.tcp(5432))

        # Grant SQS consume + S3 read/write + Bedrock embed-model invoke to the task role
        self.queue.grant_consume_messages(task_def.task_role)
        dlq.grant_send_messages(task_def.task_role)
        self.bucket.grant_read_write(task_def.task_role)
        task_def.add_to_task_role_policy(
            iam.PolicyStatement(
                actions=["bedrock:InvokeModel"],
                resources=[f"arn:aws:bedrock:{self.region}::foundation-model/{_BEDROCK_MODEL_ID}"],
            )
        )
