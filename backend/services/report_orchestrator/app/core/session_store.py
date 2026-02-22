"""
Session Store for Redis-based persistence
会话存储服务 - 基于Redis实现持久化
"""
import json
import redis
from typing import Optional, Dict, Any
from datetime import timedelta
import os
from typing import List


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

    def _session_owned_by_user(self, session_data: Dict[str, Any], user_id: Optional[str]) -> bool:
        if not user_id:
            return True
        owner_user_id = (
            session_data.get("user_id")
            or (session_data.get("request") or {}).get("user_id")
        )
        return str(owner_user_id or "") == str(user_id)

    def get_session(self, session_id: str, user_id: Optional[str] = None) -> Optional[Dict[str, Any]]:
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
            if not self._session_owned_by_user(context, user_id):
                return None
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
            timestamp_str = report_data.get('created_at', '')
            score = 0.0
            if timestamp_str:
                try:
                    from datetime import datetime
                    dt = datetime.fromisoformat(timestamp_str)
                    score = dt.timestamp()
                except ValueError:
                    print(f"[SessionStore] ⚠️  Invalid timestamp format: {timestamp_str}, using 0")
                    score = 0.0

            self.redis_client.zadd(
                'reports:all',
                {report_id: score}
            )

            print(f"[SessionStore] ✅ Saved report: {report_id}")
            return True

        except Exception as e:
            print(f"[SessionStore] ❌ Failed to save report {report_id}: {e}")
            return False

    def get_report(self, report_id: str, user_id: Optional[str] = None) -> Optional[Dict[str, Any]]:
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
            if not self._report_owned_by_user(report_data, user_id):
                return None
            print(f"[SessionStore] ✅ Retrieved report: {report_id}")
            return report_data

        except Exception as e:
            print(f"[SessionStore] ❌ Failed to get report {report_id}: {e}")
            return None

    def _report_owned_by_user(self, report_data: Dict[str, Any], user_id: Optional[str]) -> bool:
        if not user_id:
            return True
        return str(report_data.get("user_id") or "") == str(user_id)

    def get_all_reports(self, limit: int = 100, user_id: Optional[str] = None) -> list:
        """
        Get all reports (most recent first).

        Args:
            limit: Maximum number of reports to return

        Returns:
            List of report data dicts
        """
        try:
            # Get report IDs from sorted set (newest first)
            fetch_limit = max(limit * 5, limit)
            report_ids = self.redis_client.zrevrange('reports:all', 0, fetch_limit - 1)

            reports = []
            for report_id in report_ids:
                report_data = self.get_report(report_id)
                if report_data and self._report_owned_by_user(report_data, user_id):
                    reports.append(report_data)
                    if len(reports) >= limit:
                        break

            print(f"[SessionStore] ✅ Retrieved {len(reports)} reports")
            return reports

        except Exception as e:
            print(f"[SessionStore] ❌ Failed to get all reports: {e}")
            return []

    def delete_report(self, report_id: str, user_id: Optional[str] = None) -> bool:
        """
        Delete report from Redis.

        Args:
            report_id: Report identifier

        Returns:
            True if deleted, False otherwise
        """
        try:
            if self.get_report(report_id, user_id=user_id) is None:
                print(f"[SessionStore] ⚠️  Report not found: {report_id}")
                return False

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

    # ==================== Roundtable History Management ====================

    def get_roundtable_reports(self, limit: int = 50, user_id: Optional[str] = None) -> list:
        """
        Get all roundtable discussion reports (most recent first).

        Args:
            limit: Maximum number of reports to return

        Returns:
            List of roundtable report data dicts with basic info
        """
        try:
            # Get report IDs from sorted set (newest first)
            report_ids = self.redis_client.zrevrange('reports:all', 0, limit * 5 - 1)  # Get more to filter

            roundtable_reports = []
            for report_id in report_ids:
                report_data = self.get_report(report_id)
                if (
                    report_data
                    and report_data.get('type') == 'roundtable'
                    and self._report_owned_by_user(report_data, user_id)
                ):
                    # Return only essential info for list display
                    roundtable_reports.append({
                        'id': report_id,
                        'display_title': report_data.get('display_title') or report_data.get('project_name') or report_data.get('title') or report_data.get('topic', 'Unknown'),
                        'topic': report_data.get('topic', report_data.get('title', 'Unknown')),
                        'original_topic': report_data.get('original_topic', report_data.get('topic', '')),
                        'company_name': report_data.get('company_name', ''),
                        'created_at': report_data.get('created_at', ''),
                        'meeting_minutes': report_data.get('meeting_minutes', '')[:500] + '...' if len(report_data.get('meeting_minutes', '')) > 500 else report_data.get('meeting_minutes', ''),
                        'total_turns': report_data.get('discussion_summary', {}).get('total_turns', 0),
                        'participating_agents': report_data.get('discussion_summary', {}).get('participating_agents', []),
                        'config': report_data.get('config', {})
                    })

                    if len(roundtable_reports) >= limit:
                        break

            print(f"[SessionStore] ✅ Retrieved {len(roundtable_reports)} roundtable reports")
            return roundtable_reports

        except Exception as e:
            print(f"[SessionStore] ❌ Failed to get roundtable reports: {e}")
            return []

    def get_roundtable_report_full(self, report_id: str, user_id: Optional[str] = None) -> Optional[Dict[str, Any]]:
        """
        Get full roundtable report including meeting minutes for reference.

        Args:
            report_id: Report identifier

        Returns:
            Full roundtable report data if found and is roundtable type, None otherwise
        """
        try:
            report_data = self.get_report(report_id)

            if report_data is None:
                return None

            if report_data.get('type') != 'roundtable':
                print(f"[SessionStore] ⚠️  Report {report_id} is not a roundtable report")
                return None
            if not self._report_owned_by_user(report_data, user_id):
                return None

            return report_data

        except Exception as e:
            print(f"[SessionStore] ❌ Failed to get roundtable report {report_id}: {e}")
            return None

    def search_similar_roundtables(self, topic: str, limit: int = 5, user_id: Optional[str] = None) -> list:
        """
        Search for roundtable reports with similar topics.

        Args:
            topic: Search topic/keywords
            limit: Maximum number of results

        Returns:
            List of similar roundtable reports
        """
        try:
            # Get all roundtable reports
            all_roundtables = self.get_roundtable_reports(limit=100, user_id=user_id)

            # Simple keyword matching (can be enhanced with vector search later)
            topic_lower = topic.lower()
            keywords = topic_lower.split()

            scored_results = []
            for report in all_roundtables:
                report_topic = report.get('topic', '').lower()
                report_company = report.get('company_name', '').lower()

                # Calculate simple relevance score
                score = 0
                for keyword in keywords:
                    if keyword in report_topic:
                        score += 2
                    if keyword in report_company:
                        score += 1

                if score > 0:
                    scored_results.append((score, report))

            # Sort by score descending
            scored_results.sort(key=lambda x: x[0], reverse=True)

            # Return top results
            return [r[1] for r in scored_results[:limit]]

        except Exception as e:
            print(f"[SessionStore] ❌ Failed to search similar roundtables: {e}")
            return []

    # ==================== Analysis Result Caching ====================

    def _generate_cache_key(
        self,
        target: Dict[str, Any],
        scenario_id: str,
        user_id: Optional[str] = None,
    ) -> str:
        """
        Generate a cache key based on analysis target and scenario.

        Args:
            target: Analysis target (company name, symbol, etc.)
            scenario_id: Analysis scenario ID

        Returns:
            Cache key string
        """
        import hashlib
        # Create a stable hash from target data
        target_str = json.dumps(target, sort_keys=True, ensure_ascii=False)
        target_hash = hashlib.md5(target_str.encode()).hexdigest()[:12]
        user_scope = str(user_id or "anonymous")
        return f"analysis_cache:{user_scope}:{scenario_id}:{target_hash}"

    def cache_analysis_result(
        self,
        target: Dict[str, Any],
        scenario_id: str,
        result: Dict[str, Any],
        user_id: Optional[str] = None,
        ttl_hours: int = 1
    ) -> bool:
        """
        Cache analysis result for quick retrieval.

        Args:
            target: Analysis target
            scenario_id: Scenario ID
            result: Analysis result to cache
            ttl_hours: Cache TTL in hours (default 1 hour)

        Returns:
            True if successful, False otherwise
        """
        try:
            cache_key = self._generate_cache_key(target, scenario_id, user_id=user_id)
            value = json.dumps(result, ensure_ascii=False, default=str)

            self.redis_client.setex(
                cache_key,
                timedelta(hours=ttl_hours),
                value
            )

            print(f"[SessionStore] ✅ Cached analysis result: {cache_key}")
            return True

        except Exception as e:
            print(f"[SessionStore] ❌ Failed to cache analysis: {e}")
            return False

    def get_cached_analysis(
        self,
        target: Dict[str, Any],
        scenario_id: str,
        user_id: Optional[str] = None
    ) -> Optional[Dict[str, Any]]:
        """
        Retrieve cached analysis result.

        Args:
            target: Analysis target
            scenario_id: Scenario ID

        Returns:
            Cached result if found and not expired, None otherwise
        """
        try:
            cache_key = self._generate_cache_key(target, scenario_id, user_id=user_id)
            value = self.redis_client.get(cache_key)

            if value is None:
                print(f"[SessionStore] Cache miss: {cache_key}")
                return None

            result = json.loads(value)
            print(f"[SessionStore] ✅ Cache hit: {cache_key}")
            return result

        except Exception as e:
            print(f"[SessionStore] ❌ Failed to get cached analysis: {e}")
            return None

    def invalidate_analysis_cache(
        self,
        target: Dict[str, Any] = None,
        scenario_id: str = None,
        user_id: Optional[str] = None
    ) -> int:
        """
        Invalidate analysis cache.

        Args:
            target: Specific target to invalidate (optional)
            scenario_id: Specific scenario to invalidate (optional)
            If both None, invalidates all analysis caches.

        Returns:
            Number of keys deleted
        """
        try:
            if target and scenario_id:
                cache_key = self._generate_cache_key(target, scenario_id, user_id=user_id)
                return self.redis_client.delete(cache_key)
            elif scenario_id:
                if user_id:
                    pattern = f"analysis_cache:{user_id}:{scenario_id}:*"
                else:
                    pattern = f"analysis_cache:*:{scenario_id}:*"
            else:
                if user_id:
                    pattern = f"analysis_cache:{user_id}:*"
                else:
                    pattern = "analysis_cache:*"

            keys = self.redis_client.keys(pattern)
            if keys:
                deleted = self.redis_client.delete(*keys)
                print(f"[SessionStore] ✅ Invalidated {deleted} cache entries")
                return deleted
            return 0

        except Exception as e:
            print(f"[SessionStore] ❌ Failed to invalidate cache: {e}")
            return 0

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

    def list_sessions(self, limit: int = 200, user_id: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        List DD sessions (best-effort, most-recent unknown order).

        NOTE: Redis doesn't keep an index for sessions currently; this scans keys.
        Use only for lightweight dashboards/admin views.
        """
        sessions: List[Dict[str, Any]] = []
        try:
            # scan_iter avoids blocking Redis like KEYS for larger datasets.
            for key in self.redis_client.scan_iter(match="dd_session:*", count=200):
                if len(sessions) >= limit:
                    break
                raw = self.redis_client.get(key)
                if not raw:
                    continue
                try:
                    parsed = json.loads(raw)
                    if user_id:
                        session_user_id = (
                            parsed.get("user_id")
                            or (parsed.get("request") or {}).get("user_id")
                        )
                        if str(session_user_id or "") != str(user_id):
                            continue
                    sessions.append(parsed)
                except Exception:
                    continue
            return sessions
        except Exception as e:
            print(f"[SessionStore] ❌ Failed to list sessions: {e}")
            return []

    def close(self):
        """Close Redis connection."""
        try:
            self.redis_client.close()
            print("[SessionStore] ✅ Closed Redis connection")
        except Exception as e:
            print(f"[SessionStore] ❌ Failed to close connection: {e}")

    # ==================== Uploaded File Ownership ====================

    def set_uploaded_file_owner(self, file_id: str, user_id: str, ttl_days: int = 7) -> bool:
        if not file_id or not user_id:
            return False
        key = f"uploaded_file_owner:{file_id}"
        try:
            self.redis_client.setex(
                key,
                timedelta(days=ttl_days),
                str(user_id),
            )
            return True
        except Exception as e:
            print(f"[SessionStore] ❌ Failed to set file owner for {file_id}: {e}")
            return False

    def get_uploaded_file_owner(self, file_id: str) -> Optional[str]:
        if not file_id:
            return None
        key = f"uploaded_file_owner:{file_id}"
        try:
            value = self.redis_client.get(key)
            if value is None:
                return None
            return str(value)
        except Exception as e:
            print(f"[SessionStore] ❌ Failed to get file owner for {file_id}: {e}")
            return None
