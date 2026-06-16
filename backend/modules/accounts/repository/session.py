import json
from datetime import datetime
import redis.asyncio as aioredis
from redis.exceptions import ConnectionError as RedisConnectionError, TimeoutError as RedisTimeoutError
from ..models import SessionRecord, SessionStoreUnavailableException, UserRole

class SessionRepository:
    """
    aioredis (redis.asyncio) 기반의 세션 저장소 (ElastiCache Redis)
    피드백 ② 반영: Redis Connection Pool (최대 50 커넥션, 타임아웃 2초) 명시적 제어 및 Fail-Closed 예외 래핑
    """
    
    def __init__(self, redis_host: str = "localhost", redis_port: int = 6379, redis_db: int = 0):
        # 피드백 ② 반영: max_connections=50, socket_timeout=2.0 전용 풀 구성
        self._pool = aioredis.ConnectionPool(
            host=redis_host,
            port=redis_port,
            db=redis_db,
            max_connections=50,
            socket_timeout=2.0,
            decode_responses=True # 결과를 string으로 자동 디코딩
        )
        self._redis = aioredis.Redis(connection_pool=self._pool)

    def _wrap_exception(self, e: Exception) -> SessionStoreUnavailableException:
        """Redis 커넥션/타임아웃 예외를 Fail-Closed 비즈니스 예외로 래핑합니다."""
        return SessionStoreUnavailableException(f"세션 저장소(Redis)에 연결할 수 없습니다. (Fail-Closed): {str(e)}")

    async def save(self, session: SessionRecord) -> None:
        """세션 정보를 Redis에 영속화합니다. TTL은 absolute 만료 시간 기준으로 자동 세팅됩니다."""
        key = f"session:{session.handle}"
        data = {
            "handle": session.handle,
            "user_id": session.user_id,
            "created_at": session.created_at.isoformat(),
            "last_active_at": session.last_active_at.isoformat(),
            "expires_at": session.expires_at.isoformat(),
            "role": session.role
        }
        
        # absolute 만료 일시까지 남은 초 계산 (TTL)
        now = datetime.utcnow()
        ttl = int((session.expires_at - now).total_seconds())
        if ttl <= 0:
            return

        try:
            # Redis에 저장하면서 TTL 설정
            await self._redis.set(key, json.dumps(data), ex=ttl)
        except (RedisConnectionError, RedisTimeoutError) as e:
            raise self._wrap_exception(e)
        except Exception as e:
            raise SessionStoreUnavailableException(f"세션 저장 장애: {str(e)}")

    async def get(self, handle: str) -> SessionRecord | None:
        """세션 핸들러로 세션을 조회합니다."""
        key = f"session:{handle}"
        try:
            data_str = await self._redis.get(key)
            if not data_str:
                return None
            
            data = json.loads(data_str)
            return SessionRecord(
                handle=data["handle"],
                user_id=data["user_id"],
                created_at=datetime.fromisoformat(data["created_at"]),
                last_active_at=datetime.fromisoformat(data["last_active_at"]),
                expires_at=datetime.fromisoformat(data["expires_at"]),
                role=data.get("role", UserRole.USER.value)  # 구버전 레코드 호환: 누락 시 USER
            )
        except (RedisConnectionError, RedisTimeoutError) as e:
            raise self._wrap_exception(e)
        except Exception as e:
            raise SessionStoreUnavailableException(f"세션 조회 장애: {str(e)}")

    async def delete(self, handle: str) -> None:
        """세션 핸들러를 파기합니다."""
        key = f"session:{handle}"
        try:
            await self._redis.delete(key)
        except (RedisConnectionError, RedisTimeoutError) as e:
            raise self._wrap_exception(e)
        except Exception as e:
            raise SessionStoreUnavailableException(f"세션 삭제 장애: {str(e)}")
            
    async def close(self) -> None:
        """커넥션 풀을 정상 종료합니다. (App shell의 shutdown 이벤트에서 1회 호출)"""
        # redis.asyncio 는 close() 를 aclose() 로 대체(deprecated)했다. 신버전을 우선 사용하고,
        # 구버전(aclose 미존재)에서는 close() 로 폴백한다.
        aclose = getattr(self._redis, "aclose", None)
        if aclose is not None:
            await aclose()
        else:
            await self._redis.close()
        await self._pool.disconnect()
