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
    this.reconnectHandlers = []; // V5: Notify UI about reconnection attempts
    this.reconnectAttempts = 0;
    this.maxReconnectAttempts = 5;
    this.reconnectDelay = 2000; // 2 seconds
    this.config = null; // Store config for reconnection
    this.shouldReconnect = true; // Flag to control reconnection
    this.connectionState = 'disconnected'; // V5: Track connection state (disconnected, connecting, connected, reconnecting, error)
    this.lastError = null; // V5: Store last error for debugging
    this.reconnectTimeoutId = null; // V5: Track reconnection timeout
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

    // V5: Upload files first to get file_id
    if (config.uploadedFiles && config.uploadedFiles.length > 0) {
      console.log('[DD Service] Uploading files first...');
      try {
        // Upload the first file (currently only support one BP file)
        const file = config.uploadedFiles[0];
        const uploadResult = await this._uploadFile(file);

        if (uploadResult.success) {
          console.log('[DD Service] File uploaded successfully:', uploadResult.file_id);
          this.config.file_id = uploadResult.file_id;
          this.config.original_filename = uploadResult.original_filename;
        } else {
          throw new Error(uploadResult.message || '文件上传失败');
        }
      } catch (error) {
        console.error('[DD Service] File upload failed:', error);
        throw error;
      }
    }

    return this._connect();
  }

  /**
   * V5: Upload file to backend and get file_id
   * @param {File} file - File object from input
   * @returns {Promise<Object>} Upload result with file_id
   */
  async _uploadFile(file) {
    const formData = new FormData();
    formData.append('file', file);

    try {
      const response = await fetch(`${DD_API_URL}/api/upload_bp`, {
        method: 'POST',
        body: formData,
        // Don't set Content-Type header, let browser set it with boundary
      });

      if (!response.ok) {
        const errorData = await response.json().catch(() => ({ detail: response.statusText }));
        throw new Error(errorData.detail || `Upload failed: ${response.statusText}`);
      }

      return await response.json();
    } catch (error) {
      console.error('[DD Service] Upload error:', error);
      throw error;
    }
  }

  async _connect() {
    return new Promise((resolve, reject) => {
      try {
        // V5: Update connection state
        const isReconnecting = this.connectionState === 'reconnecting';
        this.connectionState = isReconnecting ? 'reconnecting' : 'connecting';

        console.log(`[DD Service] ${isReconnecting ? 'Reconnecting' : 'Connecting'} to WebSocket...`);

        // 创建WebSocket连接
        this.ws = new WebSocket(DD_WS_URL);

        this.ws.onopen = () => {
          console.log('[DD Service] WebSocket connected');
          this.connectionState = 'connected'; // V5: Update state
          this.lastError = null; // V5: Clear previous errors
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
          };

          // V5: Add file_id if file was uploaded
          if (this.config.file_id) {
            request.file_id = this.config.file_id;
            request.bp_filename = this.config.original_filename;
            console.log('[DD Service] Including file_id:', this.config.file_id);
          }

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
          this.connectionState = 'error'; // V5: Update state
          this.lastError = error; // V5: Store error
          this.errorHandlers.forEach(handler => handler(error));
        };

        this.ws.onclose = (event) => {
          console.log('[DD Service] WebSocket closed:', event.code, event.reason);

          // V5: Update connection state based on close reason
          if (event.code === 1000) {
            // Normal closure
            this.connectionState = 'disconnected';
          } else if (this.shouldReconnect) {
            // Unexpected closure, will attempt reconnect
            this.connectionState = 'reconnecting';
          } else {
            // Closure without reconnect
            this.connectionState = 'disconnected';
          }

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
    // V5: Clear any existing reconnection timeout
    if (this.reconnectTimeoutId) {
      clearTimeout(this.reconnectTimeoutId);
      this.reconnectTimeoutId = null;
    }

    if (this.reconnectAttempts < this.maxReconnectAttempts) {
      this.reconnectAttempts++;
      const delay = this.reconnectDelay * this.reconnectAttempts; // Exponential backoff

      console.log(`[DD Service] Attempting to reconnect (${this.reconnectAttempts}/${this.maxReconnectAttempts}) in ${delay}ms...`);

      // V5: Notify UI about reconnection attempt
      const reconnectInfo = {
        attempt: this.reconnectAttempts,
        maxAttempts: this.maxReconnectAttempts,
        delay: delay,
        nextAttemptAt: Date.now() + delay
      };
      this.reconnectHandlers.forEach(handler => handler(reconnectInfo));

      this.reconnectTimeoutId = setTimeout(() => {
        this.reconnectTimeoutId = null;
        this._connect().catch(err => {
          console.error('[DD Service] Reconnection failed:', err);
          this.lastError = err; // V5: Store error
          // Will trigger onclose handler which will call _attemptReconnect again if needed
        });
      }, delay);
    } else {
      console.error('[DD Service] Max reconnection attempts reached');
      this.connectionState = 'error'; // V5: Update state
      const maxReconnectError = new Error('无法重新连接到服务器，已达到最大重试次数');
      this.lastError = maxReconnectError; // V5: Store error
      this.errorHandlers.forEach(handler => handler(maxReconnectError));
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
   * V5: 注册重连处理器
   * @param {Function} handler - Receives reconnect info {attempt, maxAttempts, delay, nextAttemptAt}
   */
  onReconnect(handler) {
    this.reconnectHandlers.push(handler);
  }

  /**
   * V5: 获取当前连接状态
   * @returns {string} One of: disconnected, connecting, connected, reconnecting, error
   */
  getConnectionState() {
    return this.connectionState;
  }

  /**
   * V5: 获取最后的错误
   * @returns {Error|null} Last error or null
   */
  getLastError() {
    return this.lastError;
  }

  /**
   * V5: 手动触发重连（用于用户手动重试）
   * @returns {Promise} Connection promise
   */
  async manualReconnect() {
    console.log('[DD Service] Manual reconnect triggered by user');

    // Cancel any pending auto-reconnect
    if (this.reconnectTimeoutId) {
      clearTimeout(this.reconnectTimeoutId);
      this.reconnectTimeoutId = null;
    }

    // Reset reconnect attempts for manual retry
    this.reconnectAttempts = 0;
    this.shouldReconnect = true;
    this.lastError = null;

    // Close existing connection if any
    if (this.ws && (this.ws.readyState === WebSocket.OPEN || this.ws.readyState === WebSocket.CONNECTING)) {
      this.ws.close(1000, 'Manual reconnect');
    }

    // Attempt to reconnect
    return this._connect();
  }

  /**
   * 关闭WebSocket连接
   */
  close() {
    console.log('[DD Service] Closing WebSocket connection...');
    this.shouldReconnect = false; // Disable auto-reconnect

    // V5: Cancel any pending reconnection
    if (this.reconnectTimeoutId) {
      clearTimeout(this.reconnectTimeoutId);
      this.reconnectTimeoutId = null;
    }

    if (this.ws) {
      this.ws.close(1000, 'User closed connection'); // Normal closure
      this.ws = null;
    }

    this.connectionState = 'disconnected'; // V5: Update state
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
