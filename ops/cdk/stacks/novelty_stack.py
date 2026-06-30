"""U11 novelty-agent worker infrastructure.

Code/synth only; deploy remains a team-controlled operation. The unit is activated by
deployment configuration, not by a later manual toggle: NOVELTY_AGENT_ENABLED is always true.
"""

from aws_cdk import Duration, Stack
from aws_cdk import aws_applicationautoscaling as appscaling
from aws_cdk import aws_cloudwatch as cloudwatch
from aws_cdk import aws_ec2 as ec2
from aws_cdk import aws_ecr as ecr
from aws_cdk import aws_ecs as ecs
from aws_cdk import aws_iam as iam
from aws_cdk import aws_secretsmanager as secretsmanager
from aws_cdk import aws_sqs as sqs
from constructs import Construct

_RDS_ENDPOINT = (
    "docsuri-compute-postgres9dc8bb04-7ajkntsj0ouu"
    ".cpegcaqmu01d.ap-northeast-2.rds.amazonaws.com"
)
_RDS_PORT = 5432
_RDS_SECURITY_GROUP_ID = "sg-0633ac0c0b8c7a052"
_RDS_SECRET_ARN = (
    "arn:aws:secretsmanager:ap-northeast-2:028317349537:secret:"
    "DocsuriComputePostgresSecre-9qclXydED0pl-30WA1V"
)


class NoveltyStack(Stack):
    def __init__(
        self,
        scope: Construct,
        construct_id: str,
        *,
        vpc: ec2.IVpc,
        **kwargs,
    ) -> None:
        super().__init__(scope, construct_id, **kwargs)

        account = Stack.of(self).account
        artifact_bucket_arn = f"arn:aws:s3:::docsuri-papers-fulltext-{account}"

        dlq = sqs.Queue(
            self,
            "NoveltyJobDlq",
            queue_name="docsuri-novelty-agent-job-dlq",
            retention_period=Duration.days(14),
            encryption=sqs.QueueEncryption.SQS_MANAGED,
        )
        self.queue = sqs.Queue(
            self,
            "NoveltyJobQueue",
            queue_name="docsuri-novelty-agent-job-queue",
            visibility_timeout=Duration.seconds(900),
            retention_period=Duration.days(14),
            encryption=sqs.QueueEncryption.SQS_MANAGED,
            dead_letter_queue=sqs.DeadLetterQueue(max_receive_count=3, queue=dlq),
        )

        repo = ecr.Repository.from_repository_name(self, "ApiRepo", "docsuri-api")
        cluster = ecs.Cluster.from_cluster_attributes(
            self,
            "Cluster",
            cluster_name="docsuri",
            vpc=vpc,
            security_groups=[],
        )
        task_def = ecs.FargateTaskDefinition(self, "WorkerTaskDef", cpu=512, memory_limit_mib=1024)

        database_url = f"postgresql://docsuri_admin@{_RDS_ENDPOINT}:{_RDS_PORT}/docsuri"
        db_secret = secretsmanager.Secret.from_secret_complete_arn(
            self,
            "DbSecret",
            _RDS_SECRET_ARN,
        )

        task_def.add_container(
            "worker",
            image=ecs.ContainerImage.from_ecr_repository(repo, tag="latest"),
            command=["python", "-m", "backend.modules.novelty.worker"],
            logging=ecs.LogDrivers.aws_logs(stream_prefix="novelty-worker"),
            environment={
                "AWS_DEFAULT_REGION": self.region,
                "DATABASE_URL": database_url,
                "NOVELTY_AGENT_ENABLED": "true",
                "DOCSURI_NOVELTY_JOB_QUEUE_URL": self.queue.queue_url,
                "DOCSURI_NOVELTY_ARTIFACT_BUCKET": f"docsuri-papers-fulltext-{account}",
                "DOCSURI_NOVELTY_ARTIFACT_PREFIX": "novelty/",
                "CLOUDWATCH_NAMESPACE": "DocSuri/Production",
                "CLOUDWATCH_LOG_GROUP": "/docsuri/ops",
            },
            secrets={"PGPASSWORD": ecs.Secret.from_secrets_manager(db_secret, "password")},
        )

        self.service = ecs.FargateService(
            self,
            "WorkerService",
            service_name="docsuri-novelty-agent-worker",
            cluster=cluster,
            task_definition=task_def,
            desired_count=0,
            assign_public_ip=True,
            circuit_breaker=ecs.DeploymentCircuitBreaker(rollback=True),
            vpc_subnets=ec2.SubnetSelection(subnet_type=ec2.SubnetType.PUBLIC),
        )

        scaling = self.service.auto_scale_task_count(min_capacity=0, max_capacity=2)
        scaling.scale_on_metric(
            "SqsDepth",
            metric=self.queue.metric_approximate_number_of_messages_visible(),
            scaling_steps=[
                appscaling.ScalingInterval(upper=0, change=0),
                appscaling.ScalingInterval(lower=1, change=1),
                appscaling.ScalingInterval(lower=10, change=2),
            ],
            adjustment_type=appscaling.AdjustmentType.CHANGE_IN_CAPACITY,
        )

        rds_sg = ec2.SecurityGroup.from_security_group_id(
            self,
            "RdsSg",
            _RDS_SECURITY_GROUP_ID,
            mutable=True,
        )
        self.service.connections.allow_to(rds_sg, ec2.Port.tcp(_RDS_PORT))

        self.queue.grant_consume_messages(task_def.task_role)
        dlq.grant_send_messages(task_def.task_role)
        task_def.add_to_task_role_policy(
            iam.PolicyStatement(
                actions=["s3:GetObject", "s3:PutObject"],
                resources=[f"{artifact_bucket_arn}/novelty/*"],
            )
        )
        task_def.add_to_task_role_policy(
            iam.PolicyStatement(
                actions=["bedrock:InvokeModel", "bedrock:InvokeModelWithResponseStream"],
                resources=[
                    f"arn:aws:bedrock:{self.region}::foundation-model/anthropic.*",
                    f"arn:aws:bedrock:{self.region}:{account}:inference-profile/*",
                ],
            )
        )

        dlq.metric_approximate_number_of_messages_visible().create_alarm(
            self,
            "NoveltyDlqAlarm",
            threshold=0,
            evaluation_periods=1,
            comparison_operator=cloudwatch.ComparisonOperator.GREATER_THAN_THRESHOLD,
            treat_missing_data=cloudwatch.TreatMissingData.NOT_BREACHING,
            alarm_description="Novelty agent worker messages are landing in the DLQ",
        )
