"""Cross-account 팀 접근 (Option B) — 팀원의 자체 AWS 계정이 028317349537로 assume.

각 팀원의 홈 계정을 신뢰하고, MFA로 DocsuriCrossAccountDev를 assume → PowerUser
(IAM·결제 제외). 배포는 여전히 CI OIDC 파이프라인으로 — 이 역할은 콘솔/CLI/디버그용,
배포 크레덴셜이 아님.

신뢰 계정 목록은 app.py의 TEAM_ACCOUNT_IDS (버전 관리 → 부여/회수가 PR diff로 감사됨).
배포:
    cdk deploy Docsuri-Access"""

from aws_cdk import CfnOutput, Duration, Stack
from aws_cdk import aws_iam as iam
from constructs import Construct


class AccessStack(Stack):
    def __init__(
        self, scope: Construct, construct_id: str,
        *, account_ids: list[str], **kwargs,
    ) -> None:
        super().__init__(scope, construct_id, **kwargs)

        if not account_ids:
            raise ValueError("account_ids 비어있음 — 신뢰할 팀원 계정 ID 필요")

        # 신뢰 계정 전체에 단일 trust statement + MFA 조건 (보안 경계, 옵션 아님).
        trusted = iam.PrincipalWithConditions(
            iam.CompositePrincipal(
                *[iam.AccountPrincipal(aid) for aid in account_ids]
            ),
            {"Bool": {"aws:MultiFactorAuthPresent": "true"}},
        )

        role = iam.Role(
            self, "CrossAccountDev",
            role_name="DocsuriCrossAccountDev",
            assumed_by=trusted,
            managed_policies=[
                iam.ManagedPolicy.from_aws_managed_policy_name("PowerUserAccess"),
            ],
            # ponytail: 4h 세션 — 시간당 재-MFA 마찰 줄임, 필요시 조정
            max_session_duration=Duration.hours(4),
        )

        CfnOutput(
            self, "CrossAccountDevRoleArn",
            value=role.role_arn,
            description="팀원이 assume할 역할 ARN (CLI 프로필 role_arn에 사용)",
        )
