/**
 * DD Analysis Service
 * 处理Due Diligence分析的WebSocket连接和API调用
 */

const DD_WS_URL = 'ws://localhost:8000/ws/start_dd_analysis';
const DD_API_URL = 'http://localhost:8000';

export class DDAnalysisService {
  constructor() {
    this.ws = null;
    this.messageHandlers = [];
    this.errorHandlers = [];
    this.closeHandlers = [];
    this.reconnectAttempts = 0;
    this.maxReconnectAttempts = 5;
    this.reconnectDelay = 2000; // 2 seconds
    this.config = null; // Store config for reconnection
    this.shouldReconnect = true; // Flag to control reconnection
  }

  /**
   * 启动DD分析
   * @param {Object} config - 分析配置
   * @param {string} config.companyName - 公司名称
   * @param {string} config.projectName - 项目名称
   * @param {Array} config.selectedAgents - 选中的智能体ID列表
   * @param {Array} config.dataSources - 数据源列表
   * @param {Array} config.uploadedFiles - 上传的文件列表
   * @param {string} config.priority - 优先级
   * @param {string} config.description - 描述
   */
  async startAnalysis(config) {
    // Store config for potential reconnection
    this.config = config;
    this.shouldReconnect = true;
    this.reconnectAttempts = 0;

    return this._connect();
  }

  async _connect() {
    return new Promise((resolve, reject) => {
      try {
        console.log('[DD Service] Connecting to WebSocket...');

        // 创建WebSocket连接
        this.ws = new WebSocket(DD_WS_URL);

        this.ws.onopen = () => {
          console.log('[DD Service] WebSocket connected');
          this.reconnectAttempts = 0; // Reset on successful connection

          // 发送初始分析请求（完整配置）
          const request = {
            company_name: this.config.companyName || this.config.company || 'Unknown Company',
            user_id: 'default_user',

            // V5: Frontend configuration parameters
            project_name: this.config.projectName || `${this.config.companyName || this.config.company} Analysis`,
            selected_agents: this.config.selectedAgents || [],
            data_sources: this.config.dataSources || [],
            priority: this.config.priority || 'normal',
            description: this.config.description || ''

            // 如果有BP文件，转换为base64
            // bp_file_base64: ...,
            // bp_filename: ...,
          };

          console.log('[DD Service] Sending request:', request);
          this.ws.send(JSON.stringify(request));
          resolve({ success: true, message: 'Analysis started' });
        };

        this.ws.onmessage = (event) => {
          try {
            const data = JSON.parse(event.data);
            console.log('[DD Service] Received:', data);

            // 触发所有消息处理器
            this.messageHandlers.forEach(handler => handler(data));
          } catch (error) {
            console.error('[DD Service] Failed to parse message:', error);
          }
        };

        this.ws.onerror = (error) => {
          console.error('[DD Service] WebSocket error:', error);
          this.errorHandlers.forEach(handler => handler(error));
        };

        this.ws.onclose = (event) => {
          console.log('[DD Service] WebSocket closed:', event.code, event.reason);
          this.closeHandlers.forEach(handler => handler(event));

          // Auto-reconnect logic (unless explicitly closed by user)
          if (this.shouldReconnect && event.code !== 1000) {
            this._attemptReconnect();
          }
        };

      } catch (error) {
        console.error('[DD Service] Failed to start analysis:', error);
        reject(error);
      }
    });
  }

  _attemptReconnect() {
    if (this.reconnectAttempts < this.maxReconnectAttempts) {
      this.reconnectAttempts++;
      console.log(`[DD Service] Attempting to reconnect (${this.reconnectAttempts}/${this.maxReconnectAttempts})...`);

      setTimeout(() => {
        this._connect().catch(err => {
          console.error('[DD Service] Reconnection failed:', err);
        });
      }, this.reconnectDelay * this.reconnectAttempts); // Exponential backoff
    } else {
      console.error('[DD Service] Max reconnection attempts reached');
      this.errorHandlers.forEach(handler => handler(new Error('无法重新连接到服务器')));
    }
  }

  /**
   * 注册消息处理器
   */
  onMessage(handler) {
    this.messageHandlers.push(handler);
  }

  /**
   * 注册错误处理器
   */
  onError(handler) {
    this.errorHandlers.push(handler);
  }

  /**
   * 注册关闭处理器
   */
  onClose(handler) {
    this.closeHandlers.push(handler);
  }

  /**
   * 关闭WebSocket连接
   */
  close() {
    console.log('[DD Service] Closing WebSocket connection...');
    this.shouldReconnect = false; // Disable auto-reconnect
    if (this.ws) {
      this.ws.close(1000, 'User closed connection'); // Normal closure
      this.ws = null;
    }
  }

  /**
   * 获取DD会话状态（HTTP API）
   */
  async getSessionStatus(sessionId) {
    const response = await fetch(`${DD_API_URL}/dd_session/${sessionId}`);
    if (!response.ok) {
      throw new Error(`Failed to get session status: ${response.statusText}`);
    }
    return await response.json();
  }

  /**
   * 保存报告到后端（需要实现后端API）
   */
  async saveReport(reportData) {
    // TODO: 实现报告保存API
    const response = await fetch(`${DD_API_URL}/api/reports`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify(reportData)
    });

    if (!response.ok) {
      throw new Error(`Failed to save report: ${response.statusText}`);
    }

    return await response.json();
  }

  /**
   * 获取所有报告列表
   */
  async getReports() {
    const response = await fetch(`${DD_API_URL}/api/reports`);
    if (!response.ok) {
      throw new Error(`Failed to get reports: ${response.statusText}`);
    }
    return await response.json();
  }
}

export default new DDAnalysisService();
