"""
Session Store for Redis-based persistence
会话存储服务 - 基于Redis实现持久化
"""
import json
import redis
from typing import Optional, Dict, Any
from datetime import timedelta
import os


class SessionStore:
    """
    Redis-based session storage for DD analysis sessions and reports.

    Features:
    - Automatic expiration (TTL)
    - JSON serialization
    - Connection pooling
    - Error handling
    """

    def __init__(self, redis_url: str = None):
        """
        Initialize Redis connection.

        Args:
            redis_url: Redis connection URL (e.g., 'redis://localhost:6380')
        """
        if redis_url is None:
            redis_url = os.getenv('REDIS_URL', 'redis://redis:6379')

        self.redis_client = redis.from_url(
            redis_url,
            decode_responses=True,  # Automatically decode bytes to str
            socket_connect_timeout=5,
            socket_timeout=5
        )

        # Test connection
        try:
            self.redis_client.ping()
            print(f"[SessionStore] ✅ Connected to Redis: {redis_url}")
        except redis.ConnectionError as e:
            print(f"[SessionStore] ❌ Failed to connect to Redis: {e}")
            raise

    # ==================== Session Management ====================

    def save_session(
        self,
        session_id: str,
        context: Dict[str, Any],
        ttl_days: int = 30
    ) -> bool:
        """
        Save DD session to Redis with TTL.

        Args:
            session_id: Unique session identifier
            context: Session context (will be JSON serialized)
            ttl_days: Time to live in days (default 30 days)

        Returns:
            True if successful, False otherwise
        """
        try:
            key = f"dd_session:{session_id}"
            value = json.dumps(context, ensure_ascii=False, default=str)

            # Set with expiration
            self.redis_client.setex(
                key,
                timedelta(days=ttl_days),
                value
            )

            print(f"[SessionStore] ✅ Saved session: {session_id}")
            return True

        except Exception as e:
            print(f"[SessionStore] ❌ Failed to save session {session_id}: {e}")
            return False

    def get_session(self, session_id: str) -> Optional[Dict[str, Any]]:
        """
        Retrieve session from Redis.

        Args:
            session_id: Session identifier

        Returns:
            Session context dict if found, None otherwise
        """
        try:
            key = f"dd_session:{session_id}"
            value = self.redis_client.get(key)

            if value is None:
                print(f"[SessionStore] ⚠️  Session not found: {session_id}")
                return None

            context = json.loads(value)
            print(f"[SessionStore] ✅ Retrieved session: {session_id}")
            return context

        except Exception as e:
            print(f"[SessionStore] ❌ Failed to get session {session_id}: {e}")
            return None

    def delete_session(self, session_id: str) -> bool:
        """
        Delete session from Redis.

        Args:
            session_id: Session identifier

        Returns:
            True if deleted, False otherwise
        """
        try:
            key = f"dd_session:{session_id}"
            result = self.redis_client.delete(key)

            if result > 0:
                print(f"[SessionStore] ✅ Deleted session: {session_id}")
                return True
            else:
                print(f"[SessionStore] ⚠️  Session not found: {session_id}")
                return False

        except Exception as e:
            print(f"[SessionStore] ❌ Failed to delete session {session_id}: {e}")
            return False

    def session_exists(self, session_id: str) -> bool:
        """
        Check if session exists.

        Args:
            session_id: Session identifier

        Returns:
            True if exists, False otherwise
        """
        try:
            key = f"dd_session:{session_id}"
            return self.redis_client.exists(key) > 0
        except Exception as e:
            print(f"[SessionStore] ❌ Failed to check session {session_id}: {e}")
            return False

    def extend_session_ttl(self, session_id: str, ttl_days: int = 30) -> bool:
        """
        Extend session TTL.

        Args:
            session_id: Session identifier
            ttl_days: New TTL in days

        Returns:
            True if successful, False otherwise
        """
        try:
            key = f"dd_session:{session_id}"
            self.redis_client.expire(key, timedelta(days=ttl_days))
            print(f"[SessionStore] ✅ Extended TTL for session: {session_id}")
            return True
        except Exception as e:
            print(f"[SessionStore] ❌ Failed to extend TTL for {session_id}: {e}")
            return False

    # ==================== Report Management ====================

    def save_report(
        self,
        report_id: str,
        report_data: Dict[str, Any],
        ttl_days: int = 365
    ) -> bool:
        """
        Save report to Redis.

        Args:
            report_id: Unique report identifier
            report_data: Report data (will be JSON serialized)
            ttl_days: Time to live in days (default 1 year)

        Returns:
            True if successful, False otherwise
        """
        try:
            key = f"report:{report_id}"
            value = json.dumps(report_data, ensure_ascii=False, default=str)

            # Set with expiration
            self.redis_client.setex(
                key,
                timedelta(days=ttl_days),
                value
            )

            # Add to reports list (sorted set by timestamp)
            timestamp = report_data.get('created_at', '')
            self.redis_client.zadd(
                'reports:all',
                {report_id: float(timestamp) if timestamp else 0}
            )

            print(f"[SessionStore] ✅ Saved report: {report_id}")
            return True

        except Exception as e:
            print(f"[SessionStore] ❌ Failed to save report {report_id}: {e}")
            return False

    def get_report(self, report_id: str) -> Optional[Dict[str, Any]]:
        """
        Retrieve report from Redis.

        Args:
            report_id: Report identifier

        Returns:
            Report data dict if found, None otherwise
        """
        try:
            key = f"report:{report_id}"
            value = self.redis_client.get(key)

            if value is None:
                print(f"[SessionStore] ⚠️  Report not found: {report_id}")
                return None

            report_data = json.loads(value)
            print(f"[SessionStore] ✅ Retrieved report: {report_id}")
            return report_data

        except Exception as e:
            print(f"[SessionStore] ❌ Failed to get report {report_id}: {e}")
            return None

    def get_all_reports(self, limit: int = 100) -> list:
        """
        Get all reports (most recent first).

        Args:
            limit: Maximum number of reports to return

        Returns:
            List of report data dicts
        """
        try:
            # Get report IDs from sorted set (newest first)
            report_ids = self.redis_client.zrevrange('reports:all', 0, limit - 1)

            reports = []
            for report_id in report_ids:
                report_data = self.get_report(report_id)
                if report_data:
                    reports.append(report_data)

            print(f"[SessionStore] ✅ Retrieved {len(reports)} reports")
            return reports

        except Exception as e:
            print(f"[SessionStore] ❌ Failed to get all reports: {e}")
            return []

    def delete_report(self, report_id: str) -> bool:
        """
        Delete report from Redis.

        Args:
            report_id: Report identifier

        Returns:
            True if deleted, False otherwise
        """
        try:
            key = f"report:{report_id}"

            # Delete from reports list
            self.redis_client.zrem('reports:all', report_id)

            # Delete report data
            result = self.redis_client.delete(key)

            if result > 0:
                print(f"[SessionStore] ✅ Deleted report: {report_id}")
                return True
            else:
                print(f"[SessionStore] ⚠️  Report not found: {report_id}")
                return False

        except Exception as e:
            print(f"[SessionStore] ❌ Failed to delete report {report_id}: {e}")
            return False

    # ==================== Utility Methods ====================

    def get_stats(self) -> Dict[str, Any]:
        """
        Get Redis storage statistics.

        Returns:
            Dict with statistics
        """
        try:
            # Count sessions
            session_keys = self.redis_client.keys('dd_session:*')
            session_count = len(session_keys)

            # Count reports
            report_count = self.redis_client.zcard('reports:all')

            # Get memory info
            memory_info = self.redis_client.info('memory')
            used_memory_mb = memory_info.get('used_memory', 0) / (1024 * 1024)

            return {
                'sessions': session_count,
                'reports': report_count,
                'used_memory_mb': round(used_memory_mb, 2),
                'connection_status': 'connected'
            }

        except Exception as e:
            print(f"[SessionStore] ❌ Failed to get stats: {e}")
            return {
                'sessions': 0,
                'reports': 0,
                'used_memory_mb': 0,
                'connection_status': 'error'
            }

    def close(self):
        """Close Redis connection."""
        try:
            self.redis_client.close()
            print("[SessionStore] ✅ Closed Redis connection")
        except Exception as e:
            print(f"[SessionStore] ❌ Failed to close connection: {e}")
