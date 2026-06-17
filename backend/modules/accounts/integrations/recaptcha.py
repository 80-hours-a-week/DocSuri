import logging

import httpx

logger = logging.getLogger(__name__)

class RecaptchaClient:
    def __init__(self, secret_key: str, min_score: float = 0.5, timeout_seconds: float = 2.0):
        self._secret_key = secret_key
        self._min_score = min_score
        self._timeout_seconds = timeout_seconds
        self._verify_url = "https://www.google.com/recaptcha/api/siteverify"

    async def verify_token(self, token: str, remote_ip: str | None = None) -> bool:
        """
        Google reCAPTCHA v3 토큰의 유효성을 검증합니다.
        Fail-Closed 원칙에 따라, 통신 장애나 API 오류가 발생하면 검증 실패(False)로 판정합니다. (SEC-15)
        """
        if not self._secret_key:
            logger.warning("reCAPTCHA secret key is missing. Denying request for safety (Fail-Closed).")
            return False

        if not token:
            logger.info("reCAPTCHA token is empty. Denying request.")
            return False

        data = {
            "secret": self._secret_key,
            "response": token
        }
        if remote_ip:
            data["remoteip"] = remote_ip

        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    self._verify_url,
                    data=data,
                    timeout=self._timeout_seconds
                )
                
                if response.status_code != 200:
                    logger.error(f"reCAPTCHA verify API returned status code {response.status_code}. Fail-Closed.")
                    return False
                
                result = response.json()
                
                # 결과 무결성 체크
                success = result.get("success", False)
                score = result.get("score", 0.0)
                
                if not success:
                    error_codes = result.get("error-codes", [])
                    logger.warning(f"reCAPTCHA token validation failed. Errors: {error_codes}")
                    return False
                
                if score < self._min_score:
                    logger.warning(f"reCAPTCHA score {score} is below threshold {self._min_score}. Denying request.")
                    return False
                
                logger.info(f"reCAPTCHA verification successful. Score: {score}")
                return True

        except (httpx.HTTPError, httpx.TimeoutException) as e:
            logger.error(f"reCAPTCHA verify API communication error: {str(e)}. Fail-Closed.")
            return False
        except Exception as e:
            logger.error(f"Unexpected error during reCAPTCHA verification: {str(e)}. Fail-Closed.")
            return False
