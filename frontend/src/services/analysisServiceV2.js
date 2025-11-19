/**
 * Analysis Service V2
 * 支持5个投资场景的统一分析服务
 * - early-stage-investment
 * - growth-investment
 * - public-market-investment
 * - alternative-investment
 * - industry-research
 */

const API_BASE = 'http://localhost:8000';

class AnalysisServiceV2 {
  constructor() {
    this.ws = null;
    this.sessionId = null;
    this.reconnectAttempts = 0;
    this.maxReconnectAttempts = 3;
    this.messageHandlers = new Map();
  }

  /**
   * 获取支持的场景列表
   */
  async getScenarios() {
    try {
      const response = await fetch(`${API_BASE}/api/v2/analysis/scenarios`);
      if (!response.ok) {
        throw new Error('Failed to fetch scenarios');
      }
      const data = await response.json();
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
      const response = await fetch(`${API_BASE}/api/v2/analysis/start`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify(request)
      });

      if (!response.ok) {
        throw new Error(`API error: ${response.status}`);
      }

      const data = await response.json();
      console.log('[AnalysisV2] Analysis started:', data);

      this.sessionId = data.session_id;

      // 连接WebSocket
      await this._connectWebSocket(request);

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
  async _connectWebSocket(request) {
    return new Promise((resolve, reject) => {
      const wsUrl = `ws://localhost:8000/ws/v2/analysis/${this.sessionId}`;
      console.log('[AnalysisV2] Connecting to WebSocket:', wsUrl);

      this.ws = new WebSocket(wsUrl);

      this.ws.onopen = () => {
        console.log('[AnalysisV2] ✅ WebSocket connected');
        this.reconnectAttempts = 0;

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
        reject(error);
      };

      this.ws.onclose = (event) => {
        console.log('[AnalysisV2] WebSocket closed:', event.code, event.reason);

        if (event.code !== 1000 && this.reconnectAttempts < this.maxReconnectAttempts) {
          // 非正常关闭,尝试重连
          this.reconnectAttempts++;
          console.log(`[AnalysisV2] Reconnecting... (${this.reconnectAttempts}/${this.maxReconnectAttempts})`);
          setTimeout(() => {
            this._connectWebSocket(request);
          }, 2000 * this.reconnectAttempts);
        }
      };
    });
  }

  /**
   * 处理WebSocket消息
   */
  _handleMessage(message) {
    console.log('[AnalysisV2] Message:', message.type);

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
      const response = await fetch(`${API_BASE}/api/v2/analysis/${sessionId}/status`);
      if (!response.ok) {
        throw new Error('Failed to fetch status');
      }
      return await response.json();
    } catch (error) {
      console.error('[AnalysisV2] Error fetching status:', error);
      throw error;
    }
  }

  /**
   * 关闭连接
   */
  disconnect() {
    if (this.ws) {
      this.ws.close(1000, 'Client disconnect');
      this.ws = null;
    }
    this.messageHandlers.clear();
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
