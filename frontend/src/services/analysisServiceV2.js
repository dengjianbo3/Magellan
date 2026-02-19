/**
 * Analysis Service V2
 * 支持5个投资场景的统一分析服务
 * - early-stage-investment
 * - growth-investment
 * - public-market-investment
 * - alternative-investment
 * - industry-research
 */

import { apiUrl, WS_BASE } from '@/config/api';
import { readJsonResponse } from '@/services/httpResponse';

class AnalysisServiceV2 {
  constructor() {
    this.ws = null;
    this.sessionId = null;
    this.reconnectAttempts = 0;
    this.maxReconnectAttempts = 10; // Stage 2: 增加到10次
    this.reconnectTimer = null;
    this.messageHandlers = new Map();

    // Stage 2: 心跳机制
    this.heartbeatInterval = null;
    this.heartbeatTimeout = null;
    this.lastHeartbeat = null;
    this.HEARTBEAT_INTERVAL = 10000; // 10秒发送一次ping
    this.HEARTBEAT_TIMEOUT = 30000; // 30秒无响应则认为连接失败

    // Stage 2: 连接状态跟踪
    this.connectionState = 'disconnected'; // disconnected, connecting, connected, error, reconnecting
    this.stateChangeHandlers = [];

    // Stage 3: 消息缓冲 - 缓存早期到达的消息，等待组件mount后重放
    this.messageBuffer = [];
    this.isBuffering = true; // 初始状态下缓冲消息
  }

  /**
   * 获取认证头
   */
  _getAuthHeaders() {
    const token = this._getAccessToken();
    return token ? { 'Authorization': `Bearer ${token}` } : {};
  }

  _getAccessToken() {
    return localStorage.getItem('access_token') || '';
  }

  _getJwtExp(token) {
    if (!token) {
      return null;
    }

    try {
      const parts = token.split('.');
      if (parts.length !== 3) {
        return null;
      }

      const payload = parts[1]
        .replace(/-/g, '+')
        .replace(/_/g, '/')
        .padEnd(Math.ceil(parts[1].length / 4) * 4, '=');

      const decoded = JSON.parse(atob(payload));
      return typeof decoded.exp === 'number' ? decoded.exp : null;
    } catch (_) {
      return null;
    }
  }

  _isAccessTokenExpired(token) {
    const exp = this._getJwtExp(token);
    if (!exp) {
      return false;
    }

    const now = Math.floor(Date.now() / 1000);
    return exp <= now + 10;
  }

  _isAuthCloseEvent(event) {
    const authCloseCodes = new Set([1008, 4401, 4403]);
    const reason = String(event?.reason || '').toLowerCase();
    const reasonIndicatesAuth =
      reason.includes('auth') ||
      reason.includes('token') ||
      reason.includes('unauthorized') ||
      reason.includes('forbidden') ||
      reason.includes('expired') ||
      reason.includes('login');

    return authCloseCodes.has(event?.code) || reasonIndicatesAuth;
  }

  _emitAuthRequiredError(reason = 'Authentication required') {
    this._handleMessage({
      type: 'error',
      message: reason,
      data: {
        error: '登录已失效，请重新登录',
        code: 'AUTH_REQUIRED'
      }
    });
  }

  _clearReconnectTimer() {
    if (this.reconnectTimer) {
      clearTimeout(this.reconnectTimer);
      this.reconnectTimer = null;
    }
  }

  /**
   * 准备新分析 - 重置服务状态
   * 必须在启动新分析前调用
   */
  prepare() {
    console.log('[AnalysisV2] Preparing for new analysis session...');
    this.disconnect(); // 断开现有连接
    this.messageHandlers.clear(); // 清除旧的处理器
    this.messageBuffer = []; // 清空缓冲区
    this.isBuffering = true; // 开启缓冲模式
    this.sessionId = null;
    this.reconnectAttempts = 0;
  }

  /**
   * 获取支持的场景列表
   */
  async getScenarios() {
    try {
      const response = await fetch(apiUrl('/api/v2/analysis/scenarios'), {
        headers: {
          ...this._getAuthHeaders()
        }
      });
      const data = await readJsonResponse(response, 'Analysis scenarios');
      return data.scenarios;
    } catch (error) {
      console.error('[AnalysisV2] Error fetching scenarios:', error);
      throw error;
    }
  }

  /**
   * 启动分析任务
   * @param {Object} request - 分析请求
   * @param {string} request.project_name - 项目名称
   * @param {string} request.scenario - 投资场景
   * @param {Object} request.target - 分析目标
   * @param {Object} request.config - 分析配置
   * @param {string} request.config.depth - 分析深度 (quick/standard/comprehensive)
   */
  async startAnalysis(request) {
    try {
      console.log('[AnalysisV2] Starting analysis:', request);

      // 调用REST API启动分析
      const response = await fetch(apiUrl('/api/v2/analysis/start'), {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          ...this._getAuthHeaders()
        },
        body: JSON.stringify(request)
      });
      const data = await readJsonResponse(response, 'Start analysis');
      console.log('[AnalysisV2] Analysis started:', data);

      this.sessionId = data.session_id;

      // 连接WebSocket
      await this._connectWebSocket(request, data.ws_url);

      return {
        sessionId: data.session_id,
        estimatedDuration: data.estimated_duration,
        scenario: data.scenario,
        depth: data.depth
      };

    } catch (error) {
      console.error('[AnalysisV2] Error starting analysis:', error);
      throw error;
    }
  }

  /**
   * 连接WebSocket
   */
  async _connectWebSocket(request, serverWsUrl = null) {
    return new Promise((resolve, reject) => {
      // 添加认证token作为查询参数
      const token = this._getAccessToken();
      if (!token || this._isAccessTokenExpired(token)) {
        const authError = new Error('Authentication required: access token missing or expired');
        console.error('[AnalysisV2] Cannot connect WebSocket:', authError.message);
        this._clearReconnectTimer();
        this._setConnectionState('error');
        this._emitAuthRequiredError(authError.message);
        reject(authError);
        return;
      }

      const baseWsUrl = serverWsUrl || `${WS_BASE}/ws/v2/analysis/${this.sessionId}`;
      const wsUrl = token
        ? `${baseWsUrl}${baseWsUrl.includes('?') ? '&' : '?'}token=${encodeURIComponent(token)}`
        : baseWsUrl;
      console.log('[AnalysisV2] Connecting to WebSocket:', wsUrl);

      // Stage 2: 设置连接状态
      this._setConnectionState(this.reconnectAttempts > 0 ? 'reconnecting' : 'connecting');

      this.ws = new WebSocket(wsUrl);

      this.ws.onopen = () => {
        console.log('[AnalysisV2] ✅ WebSocket connected');
        this._clearReconnectTimer();
        this.reconnectAttempts = 0;

        // Stage 2: 设置连接状态
        this._setConnectionState('connected');

        // Stage 2: 启动心跳
        this._startHeartbeat();

        // 发送初始请求
        this.ws.send(JSON.stringify(request));
        resolve();
      };

      this.ws.onmessage = (event) => {
        try {
          const message = JSON.parse(event.data);
          this._handleMessage(message);
        } catch (error) {
          console.error('[AnalysisV2] Error parsing message:', error);
        }
      };

      this.ws.onerror = (error) => {
        console.error('[AnalysisV2] WebSocket error:', error);
        this._setConnectionState('error');
        reject(error);
      };

      this.ws.onclose = (event) => {
        console.log('[AnalysisV2] WebSocket closed:', event.code, event.reason);

        // Stage 2: 停止心跳
        this._stopHeartbeat();

        if (this._isAuthCloseEvent(event)) {
          console.error('[AnalysisV2] Authentication failure on WebSocket, stop reconnecting');
          this._clearReconnectTimer();
          this._setConnectionState('error');
          this._emitAuthRequiredError(event.reason || 'Authentication required');
          return;
        }

        if (event.code !== 1000 && this.reconnectAttempts < this.maxReconnectAttempts) {
          // 非正常关闭,尝试重连
          this.reconnectAttempts++;
          console.log(`[AnalysisV2] Reconnecting... (${this.reconnectAttempts}/${this.maxReconnectAttempts})`);

          // Stage 2: 指数退避策略 - 1s, 2s, 4s, 8s, 16s...
          const backoffDelay = Math.min(1000 * Math.pow(2, this.reconnectAttempts - 1), 16000);

          this._setConnectionState('reconnecting');

          this._clearReconnectTimer();
          this.reconnectTimer = setTimeout(() => {
            this._connectWebSocket(request, serverWsUrl).catch(error => {
              console.error('[AnalysisV2] Reconnect failed:', error);
            });
          }, backoffDelay);
        } else if (this.reconnectAttempts >= this.maxReconnectAttempts) {
          console.error('[AnalysisV2] Max reconnection attempts reached');
          this._clearReconnectTimer();
          this._setConnectionState('error');
        } else {
          this._clearReconnectTimer();
          this._setConnectionState('disconnected');
        }
      };
    });
  }

  /**
   * 处理WebSocket消息
   */
  _handleMessage(message) {
    // Stage 2: 处理心跳响应
    if (message.type === 'pong') {
      this.lastHeartbeat = Date.now();
      this._resetHeartbeatTimeout();
      return; // pong消息不需要传递给业务handlers
    }

    console.log('[AnalysisV2] Message:', message.type);

    // Stage 3: 如果正在缓冲模式，将重要消息存储到缓冲区
    if (this.isBuffering && this._isImportantMessage(message.type)) {
      console.log('[AnalysisV2] Buffering message:', message.type);
      this.messageBuffer.push(message);
      return; // 暂不分发，等待flush时再处理
    }

    // 分发消息给handlers
    this._dispatchMessage(message);
  }

  /**
   * Stage 3: 判断是否为重要消息（需要缓冲）
   */
  _isImportantMessage(type) {
    const importantTypes = [
      'workflow_start',
      'step_start',
      'step_complete',
      'agent_event',
      'status_update',
      'error',  // 错误消息必须立即处理
      'complete',  // 完成消息也应该立即处理
      'quick_judgment_complete', // Stage 4: 快速判断完成
      'analysis_complete' // Stage 4: 标准分析完成
    ];
    return importantTypes.includes(type);
  }

  /**
   * Stage 3: 分发消息给handlers
   */
  _dispatchMessage(message) {
    // 调用对应类型的handler
    const handlers = this.messageHandlers.get(message.type) || [];
    handlers.forEach(handler => {
      try {
        handler(message);
      } catch (error) {
        console.error('[AnalysisV2] Handler error:', error);
      }
    });

    // 调用通用handler
    const allHandlers = this.messageHandlers.get('*') || [];
    allHandlers.forEach(handler => {
      try {
        handler(message);
      } catch (error) {
        console.error('[AnalysisV2] Handler error:', error);
      }
    });
  }

  /**
   * Stage 3: 刷新缓冲区，重放所有缓存的消息
   * 应该在组件mount后立即调用
   */
  flushMessageBuffer() {
    console.log('[AnalysisV2] Flushing message buffer, count:', this.messageBuffer.length);

    // 停止缓冲
    this.isBuffering = false;

    // 重放所有缓存的消息
    const messages = [...this.messageBuffer];
    this.messageBuffer = [];

    messages.forEach(message => {
      console.log('[AnalysisV2] Replaying buffered message:', message.type);
      this._dispatchMessage(message);
    });
  }

  /**
   * Stage 3: 开始缓冲新消息（用于重新连接等场景）
   */
  startBuffering() {
    this.isBuffering = true;
    this.messageBuffer = [];
  }

  /**
   * Stage 2: 启动心跳机制
   */
  _startHeartbeat() {
    this._stopHeartbeat(); // 清理旧的心跳

    // 每10秒发送一次ping
    this.heartbeatInterval = setInterval(() => {
      if (this.ws && this.ws.readyState === WebSocket.OPEN) {
        console.log('[AnalysisV2] 💓 Sending heartbeat ping');
        this.ws.send(JSON.stringify({ type: 'ping' }));
        this._resetHeartbeatTimeout();
      }
    }, this.HEARTBEAT_INTERVAL);

    // 立即发送一次ping
    if (this.ws && this.ws.readyState === WebSocket.OPEN) {
      this.ws.send(JSON.stringify({ type: 'ping' }));
      this._resetHeartbeatTimeout();
    }
  }

  /**
   * Stage 2: 停止心跳机制
   */
  _stopHeartbeat() {
    if (this.heartbeatInterval) {
      clearInterval(this.heartbeatInterval);
      this.heartbeatInterval = null;
    }
    if (this.heartbeatTimeout) {
      clearTimeout(this.heartbeatTimeout);
      this.heartbeatTimeout = null;
    }
  }

  /**
   * Stage 2: 重置心跳超时计时器
   */
  _resetHeartbeatTimeout() {
    if (this.heartbeatTimeout) {
      clearTimeout(this.heartbeatTimeout);
    }

    // 30秒内没有收到pong则认为连接已断
    this.heartbeatTimeout = setTimeout(() => {
      console.error('[AnalysisV2] ❌ Heartbeat timeout - connection lost');
      if (this.ws) {
        this.ws.close(4000, 'Heartbeat timeout');
      }
    }, this.HEARTBEAT_TIMEOUT);
  }

  /**
   * Stage 2: 设置连接状态
   */
  _setConnectionState(newState) {
    if (this.connectionState !== newState) {
      const oldState = this.connectionState;
      this.connectionState = newState;
      console.log(`[AnalysisV2] Connection state: ${oldState} → ${newState}`);

      // 通知所有状态变化监听器
      this.stateChangeHandlers.forEach(handler => {
        try {
          handler(newState, oldState);
        } catch (error) {
          console.error('[AnalysisV2] State change handler error:', error);
        }
      });
    }
  }

  /**
   * Stage 2: 监听连接状态变化
   */
  onStateChange(handler) {
    this.stateChangeHandlers.push(handler);
    // 立即调用一次,传递当前状态
    handler(this.connectionState, null);
  }

  /**
   * Stage 2: 移除状态变化监听器
   */
  offStateChange(handler) {
    const index = this.stateChangeHandlers.indexOf(handler);
    if (index !== -1) {
      this.stateChangeHandlers.splice(index, 1);
    }
  }

  /**
   * Stage 2: 获取当前连接状态
   */
  getConnectionState() {
    return this.connectionState;
  }

  /**
   * 注册消息处理器
   * @param {string} type - 消息类型 ('*'表示所有消息)
   * @param {Function} handler - 处理函数
   */
  on(type, handler) {
    if (!this.messageHandlers.has(type)) {
      this.messageHandlers.set(type, []);
    }
    this.messageHandlers.get(type).push(handler);
  }

  /**
   * 移除消息处理器
   */
  off(type, handler) {
    const handlers = this.messageHandlers.get(type);
    if (handlers) {
      const index = handlers.indexOf(handler);
      if (index !== -1) {
        handlers.splice(index, 1);
      }
    }
  }

  /**
   * 获取分析状态
   */
  async getStatus(sessionId) {
    try {
      const response = await fetch(apiUrl(`/api/v2/analysis/${sessionId}/status`), {
        headers: {
          ...this._getAuthHeaders()
        }
      });
      return await readJsonResponse(response, 'Analysis status');
    } catch (error) {
      console.error('[AnalysisV2] Error fetching status:', error);
      throw error;
    }
  }

  /**
   * 升级到标准分析
   * 重新启动分析，使用standard深度
   * @param {Object} params - 升级参数
   * @param {string} params.projectName - 项目名称
   * @param {string} params.scenarioId - 场景ID
   * @param {Object} params.target - 分析目标
   * @param {Object} params.originalConfig - 原始配置
   */
  async upgradeToStandard({ projectName, scenarioId, target, originalConfig }) {
    console.log('[AnalysisV2] Upgrading to standard analysis...');

    // 准备新的分析请求
    this.prepare();

    const request = {
      project_name: projectName,
      scenario: scenarioId,
      target: target,
      config: {
        ...originalConfig,
        depth: 'standard' // 升级到标准深度
      }
    };

    return await this.startAnalysis(request);
  }

  /**
   * 关闭连接
   */
  disconnect() {
    // Stage 2: 停止心跳
    this._stopHeartbeat();
    this._clearReconnectTimer();
    this.reconnectAttempts = 0;

    if (this.ws) {
      this.ws.close(1000, 'Client disconnect');
      this.ws = null;
    }
    this.messageHandlers.clear();
    this._setConnectionState('disconnected');
  }

  /**
   * 获取连接状态
   */
  isConnected() {
    return this.ws && this.ws.readyState === WebSocket.OPEN;
  }
}

// 导出单例
export default new AnalysisServiceV2();
