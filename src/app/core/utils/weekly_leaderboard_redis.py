import json
from datetime import date
from typing import Optional, Dict
from redis.asyncio import Redis

from ...core.logger import logging
from .rate_limit import rate_limiter

logger = logging.getLogger(__name__)


class WeeklyLeaderboardRedis:
    """Helper class for managing weekly leaderboard state in Redis"""
    
    @staticmethod
    def _get_state_key(week_start: date) -> str:
        return f"weekly_leaderboard:state:{week_start.isoformat()}"
    
    @staticmethod
    def _get_dummy_key(week_start: date, dummy_id: str) -> str:
        return f"weekly_leaderboard:dummy:{week_start.isoformat()}:{dummy_id}"
    
    @staticmethod
    def _get_rank_key(week_start: date, user_id: str) -> str:
        return f"weekly_leaderboard:rank:{week_start.isoformat()}:{user_id}"
    
    @staticmethod
    async def get_state(week_start: date) -> Optional[Dict]:
        """Get weekly leaderboard state"""
        try:
            client = rate_limiter.get_client()
            key = WeeklyLeaderboardRedis._get_state_key(week_start)
            data = await client.get(key)
            if data:
                return json.loads(data)
            return None
        except Exception as e:
            logger.exception(f"Error getting weekly leaderboard state for {week_start}: {e}")
            return None
    
    @staticmethod
    async def set_state(week_start: date, state: Dict, ttl: int = 604800) -> None:
        """Set weekly leaderboard state (TTL: 7 days)"""
        try:
            client = rate_limiter.get_client()
            key = WeeklyLeaderboardRedis._get_state_key(week_start)
            await client.setex(key, ttl, json.dumps(state))
        except Exception as e:
            logger.exception(f"Error setting weekly leaderboard state for {week_start}: {e}")
            raise
    
    @staticmethod
    async def get_dummy(week_start: date, dummy_id: str) -> Optional[Dict]:
        """Get dummy user state"""
        try:
            client = rate_limiter.get_client()
            key = WeeklyLeaderboardRedis._get_dummy_key(week_start, dummy_id)
            data = await client.get(key)
            if data:
                return json.loads(data)
            return None
        except Exception as e:
            logger.exception(f"Error getting dummy {dummy_id} for {week_start}: {e}")
            return None
    
    @staticmethod
    async def set_dummy(week_start: date, dummy_id: str, dummy_data: Dict, ttl: int = 604800) -> None:
        """Set dummy user state"""
        try:
            client = rate_limiter.get_client()
            key = WeeklyLeaderboardRedis._get_dummy_key(week_start, dummy_id)
            await client.setex(key, ttl, json.dumps(dummy_data))
        except Exception as e:
            logger.exception(f"Error setting dummy {dummy_id} for {week_start}: {e}")
            raise
    
    @staticmethod
    async def get_previous_rank(week_start: date, user_id: str) -> Optional[int]:
        """Get user's previous rank from cache"""
        try:
            client = rate_limiter.get_client()
            key = WeeklyLeaderboardRedis._get_rank_key(week_start, str(user_id))
            rank = await client.get(key)
            return int(rank) if rank else None
        except Exception as e:
            logger.exception(f"Error getting previous rank for user {user_id} on {week_start}: {e}")
            return None
    
    @staticmethod
    async def set_previous_rank(week_start: date, user_id: str, rank: int, ttl: int = 604800) -> None:
        """Set user's rank for next comparison"""
        try:
            client = rate_limiter.get_client()
            key = WeeklyLeaderboardRedis._get_rank_key(week_start, str(user_id))
            await client.setex(key, ttl, str(rank))
        except Exception as e:
            logger.exception(f"Error setting previous rank for user {user_id} on {week_start}: {e}")
            raise

