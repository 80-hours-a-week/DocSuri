import asyncio
import logging
import os
from abc import ABC, abstractmethod

logger = logging.getLogger(__name__)

class EmailClientInterface(ABC):
    @abstractmethod
    async def send_verification_email(self, email: str, token: str, signup_link: str) -> bool:
        """이메일 인증 링크를 사용자에게 발송합니다."""
        pass


class MockEmailClient(EmailClientInterface):
    """로컬 테스트를 위해 실제 이메일을 발송하지 않고 터미널 콘솔에 출력하는 Mock 이메일 클라이언트"""
    
    async def send_verification_email(self, email: str, token: str, signup_link: str) -> bool:
        logger.info("================ [MOCK EMAIL DELIVERY] ================")
        logger.info(f"To: {email}")
        logger.info("Subject: DocSuri 이메일 인증 안내")
        logger.info(f"Verification Token: {token}")
        logger.info(f"Verification Link: {signup_link}?token={token}")
        logger.info("=========================================================")
        return True


class SESEmailClient(EmailClientInterface):
    """boto3를 활용해 Amazon SES를 통해 이메일을 전송하는 프로덕션 이메일 클라이언트"""
    
    def __init__(self, sender_email: str, region_name: str = "ap-northeast-2", observability_hub = None):
        self._sender_email = sender_email
        self._region_name = region_name
        self._observability_hub = observability_hub
        self._client = None

    def _get_client(self):
        if self._client is None:
            import boto3
            # 컨테이너에 투과 주입된 IAM Role 또는 기본 자격 증명 사용
            self._client = boto3.client("ses", region_name=self._region_name)
        return self._client

    async def send_verification_email(self, email: str, token: str, signup_link: str) -> bool:
        """
        Amazon SES를 통해 인증 메일을 전송합니다.
        실패 시 트랜잭션을 중단시키지 않는 소프트 폴백(Soft-Fallback) 정책을 적용합니다 (Q2 답변 반영).
        이메일 발송이 실패하면 EmailDeliveryFailureSignal 경보 메트릭을 발행하고 False를 반환합니다.
        """
        link = f"{signup_link}?token={token}"
        subject = "[DocSuri] 계정 활성화를 위한 이메일 인증 링크"
        body_text = f"안녕하세요. DocSuri 가입을 완료하려면 다음 링크를 24시간 이내에 클릭해 주세요.\n\n{link}"
        body_html = f"""
        <html>
            <body>
                <h3>DocSuri 가입을 환영합니다!</h3>
                <p>아래 링크를 클릭하여 계정 활성화를 완료해 주세요 (24시간 동안 유효합니다).</p>
                <p><a href="{link}">계정 활성화하기</a></p>
                <p>만약 링크 클릭이 안 된다면 다음 주소를 브라우저에 복사해 넣어주세요:</p>
                <p>{link}</p>
            </body>
        </html>
        """
        
        try:
            ses = self._get_client()

            # boto3 SES 호출은 동기 블로킹 네트워크 I/O다. async 핸들러에서 직접 호출하면 응답 동안
            # 이벤트 루프 전체가 멈춰 동시 요청이 정체되므로, asyncio.to_thread로 워커 스레드에 위임한다.
            response = await asyncio.to_thread(
                lambda: ses.send_email(
                    Source=self._sender_email,
                    Destination={
                        "ToAddresses": [email]
                    },
                    Message={
                        "Subject": {
                            "Data": subject,
                            "Charset": "UTF-8"
                        },
                        "Body": {
                            "Text": {
                                "Data": body_text,
                                "Charset": "UTF-8"
                            },
                            "Html": {
                                "Data": body_html,
                                "Charset": "UTF-8"
                            }
                        }
                    }
                )
            )
            message_id = response.get("MessageId")
            logger.info(f"Verification email sent successfully via SES to {email}. MessageId: {message_id}")
            return True
            
        except Exception as e:
            # 소프트 폴백: SES 메일 발송이 실패하더라도 회원가입 DB 트랜잭션을 중단(Rollback)시키지 않음.
            # 실패를 수집 및 경보하기 위한 신호(EmailDeliveryFailureSignal) 수집
            logger.error(f"Amazon SES 이메일 발송 실패 (Soft-Fallback 활성): {str(e)}")
            
            if self._observability_hub:
                try:
                    # docsuri_shared.ports.ObservabilityHub 포트(snake_case)로 실패 신호 전송
                    self._observability_hub.emit_metric(
                        "EmailDeliveryFailureSignal",
                        1,
                        {"error_type": type(e).__name__}
                    )
                    self._observability_hub.emit_log({
                        "event": "EmailDeliveryFailureSignal",
                        "error_type": type(e).__name__,
                        "message": "SES email dispatch failed. Account remains PENDING."
                    })
                except Exception as trace_err:
                    logger.critical(f"ObservabilityHub 수집기 마저 장애 상태 발생: {str(trace_err)}")
            
            return False


def get_email_client(env: str = "production", sender_email: str = "", region: str = "ap-northeast-2", observability_hub = None) -> EmailClientInterface:
    """환경변수 혹은 스위치 설정에 따라 이메일 클라이언트 인스턴스를 스위칭하여 반환합니다."""
    is_mock = os.getenv("SES_MOCK", "false").lower() == "true" or env.lower() == "local"
    if is_mock:
        logger.info("Using MockEmailClient for account verification link.")
        return MockEmailClient()
    else:
        logger.info("Using production SESEmailClient for account verification link.")
        return SESEmailClient(sender_email=sender_email, region_name=region, observability_hub=observability_hub)
