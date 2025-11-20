/**
 * Session Manager - Stage 2
 * 管理分析会话的持久化存储和恢复
 *
 * 功能:
 * - 保存会话到LocalStorage
 * - 从LocalStorage恢复会话
 * - 会话历史管理
 * - 过期会话清理
 */

const STORAGE_KEY = 'magellan_sessions';
const MAX_SESSION_AGE_DAYS = 30; // 会话最长保留30天

class SessionManager {
  constructor() {
    this._ensureStorage();
  }

  /**
   * 确保LocalStorage中存在sessions对象
   */
  _ensureStorage() {
    try {
      const existing = localStorage.getItem(STORAGE_KEY);
      if (!existing) {
        localStorage.setItem(STORAGE_KEY, JSON.stringify({}));
      }
    } catch (error) {
      console.error('[SessionManager] Failed to initialize storage:', error);
    }
  }

  /**
   * 获取所有会话
   */
  _getAllSessions() {
    try {
      const data = localStorage.getItem(STORAGE_KEY);
      return data ? JSON.parse(data) : {};
    } catch (error) {
      console.error('[SessionManager] Failed to get sessions:', error);
      return {};
    }
  }

  /**
   * 保存所有会话
   */
  _saveAllSessions(sessions) {
    try {
      localStorage.setItem(STORAGE_KEY, JSON.stringify(sessions));
    } catch (error) {
      console.error('[SessionManager] Failed to save sessions:', error);
      throw error;
    }
  }

  /**
   * 保存会话
   * @param {Object} sessionData - 会话数据
   * @param {string} sessionData.sessionId - 会话ID
   * @param {string} sessionData.projectName - 项目名称
   * @param {Object} sessionData.scenario - 场景配置
   * @param {Object} sessionData.targetData - 目标数据
   * @param {Object} sessionData.configData - 配置数据
   * @param {string} sessionData.status - 状态 (pending/running/completed/failed)
   * @param {number} sessionData.progress - 进度 (0-100)
   * @param {number} sessionData.currentStep - 当前步骤
   */
  saveSession(sessionData) {
    try {
      const sessions = this._getAllSessions();
      const now = Date.now();

      // 构建完整的会话对象
      const session = {
        sessionId: sessionData.sessionId,
        projectName: sessionData.projectName,
        scenario: sessionData.scenario,
        targetData: sessionData.targetData,
        configData: sessionData.configData,
        status: sessionData.status || 'pending',
        progress: sessionData.progress || 0,
        currentStep: sessionData.currentStep || 0,
        startedAt: sessionData.startedAt || now,
        updatedAt: now,
        completedAt: sessionData.completedAt || null
      };

      sessions[sessionData.sessionId] = session;
      this._saveAllSessions(sessions);

      console.log('[SessionManager] Session saved:', sessionData.sessionId);
      return session;
    } catch (error) {
      console.error('[SessionManager] Failed to save session:', error);
      throw error;
    }
  }

  /**
   * 更新会话状态
   * @param {string} sessionId - 会话ID
   * @param {Object} updates - 要更新的字段
   */
  updateSession(sessionId, updates) {
    try {
      const sessions = this._getAllSessions();
      const session = sessions[sessionId];

      if (!session) {
        console.warn('[SessionManager] Session not found:', sessionId);
        return null;
      }

      // 更新字段
      Object.assign(session, updates, {
        updatedAt: Date.now()
      });

      // 如果状态变为completed,记录完成时间
      if (updates.status === 'completed' && !session.completedAt) {
        session.completedAt = Date.now();
      }

      sessions[sessionId] = session;
      this._saveAllSessions(sessions);

      console.log('[SessionManager] Session updated:', sessionId, updates);
      return session;
    } catch (error) {
      console.error('[SessionManager] Failed to update session:', error);
      throw error;
    }
  }

  /**
   * 获取会话
   * @param {string} sessionId - 会话ID
   */
  getSession(sessionId) {
    try {
      const sessions = this._getAllSessions();
      return sessions[sessionId] || null;
    } catch (error) {
      console.error('[SessionManager] Failed to get session:', error);
      return null;
    }
  }

  /**
   * 删除会话
   * @param {string} sessionId - 会话ID
   */
  deleteSession(sessionId) {
    try {
      const sessions = this._getAllSessions();
      if (sessions[sessionId]) {
        delete sessions[sessionId];
        this._saveAllSessions(sessions);
        console.log('[SessionManager] Session deleted:', sessionId);
        return true;
      }
      return false;
    } catch (error) {
      console.error('[SessionManager] Failed to delete session:', error);
      return false;
    }
  }

  /**
   * 获取所有会话列表
   * @param {Object} options - 选项
   * @param {number} options.limit - 最大返回数量
   * @param {string} options.status - 按状态过滤
   * @param {string} options.sortBy - 排序字段 (startedAt/updatedAt)
   * @param {string} options.order - 排序顺序 (asc/desc)
   */
  getAllSessions(options = {}) {
    try {
      const {
        limit = 100,
        status = null,
        sortBy = 'updatedAt',
        order = 'desc'
      } = options;

      const sessions = this._getAllSessions();
      let sessionList = Object.values(sessions);

      // 按状态过滤
      if (status) {
        sessionList = sessionList.filter(s => s.status === status);
      }

      // 排序
      sessionList.sort((a, b) => {
        const aValue = a[sortBy] || 0;
        const bValue = b[sortBy] || 0;
        return order === 'asc' ? aValue - bValue : bValue - aValue;
      });

      // 限制数量
      if (limit > 0) {
        sessionList = sessionList.slice(0, limit);
      }

      return sessionList;
    } catch (error) {
      console.error('[SessionManager] Failed to get all sessions:', error);
      return [];
    }
  }

  /**
   * 获取最近的会话
   * @param {number} limit - 返回数量
   */
  getRecentSessions(limit = 10) {
    return this.getAllSessions({
      limit,
      sortBy: 'updatedAt',
      order: 'desc'
    });
  }

  /**
   * 获取正在运行的会话
   */
  getActiveSessions() {
    return this.getAllSessions({
      status: 'running',
      sortBy: 'startedAt',
      order: 'desc'
    });
  }

  /**
   * 获取已完成的会话
   * @param {number} limit - 返回数量
   */
  getCompletedSessions(limit = 10) {
    return this.getAllSessions({
      status: 'completed',
      limit,
      sortBy: 'completedAt',
      order: 'desc'
    });
  }

  /**
   * 清理过期会话
   * @param {number} maxAgeDays - 最大保留天数
   */
  cleanExpiredSessions(maxAgeDays = MAX_SESSION_AGE_DAYS) {
    try {
      const sessions = this._getAllSessions();
      const now = Date.now();
      const maxAgeMs = maxAgeDays * 24 * 60 * 60 * 1000;
      let cleaned = 0;

      Object.keys(sessions).forEach(sessionId => {
        const session = sessions[sessionId];
        const age = now - (session.updatedAt || session.startedAt || 0);

        if (age > maxAgeMs) {
          delete sessions[sessionId];
          cleaned++;
        }
      });

      if (cleaned > 0) {
        this._saveAllSessions(sessions);
        console.log(`[SessionManager] Cleaned ${cleaned} expired sessions`);
      }

      return cleaned;
    } catch (error) {
      console.error('[SessionManager] Failed to clean expired sessions:', error);
      return 0;
    }
  }

  /**
   * 清除所有会话
   */
  clearAllSessions() {
    try {
      localStorage.setItem(STORAGE_KEY, JSON.stringify({}));
      console.log('[SessionManager] All sessions cleared');
      return true;
    } catch (error) {
      console.error('[SessionManager] Failed to clear sessions:', error);
      return false;
    }
  }

  /**
   * 导出会话数据 (用于备份或调试)
   */
  exportSessions() {
    try {
      const sessions = this._getAllSessions();
      return JSON.stringify(sessions, null, 2);
    } catch (error) {
      console.error('[SessionManager] Failed to export sessions:', error);
      return null;
    }
  }

  /**
   * 导入会话数据 (用于恢复)
   * @param {string} jsonData - JSON格式的会话数据
   */
  importSessions(jsonData) {
    try {
      const sessions = JSON.parse(jsonData);
      this._saveAllSessions(sessions);
      console.log('[SessionManager] Sessions imported successfully');
      return true;
    } catch (error) {
      console.error('[SessionManager] Failed to import sessions:', error);
      return false;
    }
  }

  /**
   * 获取存储统计信息
   */
  getStorageStats() {
    try {
      const sessions = this._getAllSessions();
      const sessionList = Object.values(sessions);

      const stats = {
        total: sessionList.length,
        byStatus: {
          pending: 0,
          running: 0,
          completed: 0,
          failed: 0
        },
        oldestSession: null,
        newestSession: null,
        storageSize: JSON.stringify(sessions).length
      };

      sessionList.forEach(session => {
        stats.byStatus[session.status] = (stats.byStatus[session.status] || 0) + 1;

        if (!stats.oldestSession || session.startedAt < stats.oldestSession.startedAt) {
          stats.oldestSession = session;
        }
        if (!stats.newestSession || session.startedAt > stats.newestSession.startedAt) {
          stats.newestSession = session;
        }
      });

      return stats;
    } catch (error) {
      console.error('[SessionManager] Failed to get storage stats:', error);
      return null;
    }
  }
}

// 导出单例
export default new SessionManager();
