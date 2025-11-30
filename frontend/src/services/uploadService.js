/**
 * File Upload Service
 * Stage 1 implementation for file upload functionality
 * Supports: BP files, Financial data, Public market filings
 */

// Environment variable for API base URL
const API_BASE = import.meta.env.VITE_API_BASE || 'http://localhost:8000';

class UploadService {
  /**
   * Upload Business Plan file
   * @param {File} file - The file to upload
   * @param {Function} onProgress - Progress callback (optional)
   * @returns {Promise<Object>} Upload result with file_id
   */
  async uploadBusinessPlan(file, onProgress = null) {
    try {
      const formData = new FormData();
      formData.append('file', file);

      const response = await this._uploadWithProgress(
        `${API_BASE}/api/v2/upload/bp`,
        formData,
        onProgress
      );

      return response;
    } catch (error) {
      console.error('[UploadService] BP upload failed:', error);
      throw new Error(`上传失败: ${error.message}`);
    }
  }

  /**
   * Upload Financial Data file
   * @param {File} file - The file to upload
   * @param {Function} onProgress - Progress callback (optional)
   * @returns {Promise<Object>} Upload result with file_id
   */
  async uploadFinancialData(file, onProgress = null) {
    try {
      const formData = new FormData();
      formData.append('file', file);

      const response = await this._uploadWithProgress(
        `${API_BASE}/api/v2/upload/financial`,
        formData,
        onProgress
      );

      return response;
    } catch (error) {
      console.error('[UploadService] Financial upload failed:', error);
      throw new Error(`上传失败: ${error.message}`);
    }
  }

  /**
   * Upload Public Market Filings (multiple files)
   * @param {File[]} files - Array of files to upload
   * @param {Function} onProgress - Progress callback (optional)
   * @returns {Promise<Object>} Upload result with file_ids array
   */
  async uploadFilings(files, onProgress = null) {
    try {
      const formData = new FormData();

      // Append all files
      files.forEach(file => {
        formData.append('files', file);
      });

      const response = await this._uploadWithProgress(
        `${API_BASE}/api/v2/upload/filings`,
        formData,
        onProgress
      );

      return response;
    } catch (error) {
      console.error('[UploadService] Filings upload failed:', error);
      throw new Error(`上传失败: ${error.message}`);
    }
  }

  /**
   * Internal method to upload with progress tracking
   * Uses XMLHttpRequest to support progress events
   * @private
   */
  _uploadWithProgress(url, formData, onProgress) {
    return new Promise((resolve, reject) => {
      const xhr = new XMLHttpRequest();

      // Progress event
      if (onProgress && xhr.upload) {
        xhr.upload.addEventListener('progress', (e) => {
          if (e.lengthComputable) {
            const percentComplete = Math.round((e.loaded / e.total) * 100);
            onProgress(percentComplete);
          }
        });
      }

      // Load event (success)
      xhr.addEventListener('load', () => {
        if (xhr.status >= 200 && xhr.status < 300) {
          try {
            const response = JSON.parse(xhr.responseText);
            resolve(response);
          } catch (e) {
            reject(new Error('Invalid response format'));
          }
        } else {
          try {
            const error = JSON.parse(xhr.responseText);
            reject(new Error(error.detail || `Upload failed with status ${xhr.status}`));
          } catch (e) {
            reject(new Error(`Upload failed with status ${xhr.status}`));
          }
        }
      });

      // Error event
      xhr.addEventListener('error', () => {
        reject(new Error('Network error occurred during upload'));
      });

      // Abort event
      xhr.addEventListener('abort', () => {
        reject(new Error('Upload was cancelled'));
      });

      // Timeout event
      xhr.addEventListener('timeout', () => {
        reject(new Error('Upload timed out'));
      });

      // Open and send request
      xhr.open('POST', url);
      xhr.timeout = 120000; // 2 minutes timeout
      xhr.send(formData);
    });
  }

  /**
   * Validate file before upload
   * @param {File} file - The file to validate
   * @param {Object} options - Validation options
   * @returns {Object} Validation result {valid: boolean, error: string}
   */
  validateFile(file, options = {}) {
    const {
      maxSize = 50 * 1024 * 1024, // 50MB default
      allowedExtensions = []
    } = options;

    // Check file size
    if (file.size > maxSize) {
      const sizeMB = (file.size / (1024 * 1024)).toFixed(2);
      const maxSizeMB = (maxSize / (1024 * 1024)).toFixed(0);
      return {
        valid: false,
        error: `文件过大 (${sizeMB}MB)。最大允许: ${maxSizeMB}MB`
      };
    }

    // Check file extension
    if (allowedExtensions.length > 0) {
      const fileExt = file.name.substring(file.name.lastIndexOf('.')).toLowerCase();
      if (!allowedExtensions.includes(fileExt)) {
        return {
          valid: false,
          error: `不支持的文件类型: ${fileExt}。支持: ${allowedExtensions.join(', ')}`
        };
      }
    }

    return { valid: true };
  }

  /**
   * Format file size for display
   * @param {number} bytes - File size in bytes
   * @returns {string} Formatted file size
   */
  formatFileSize(bytes) {
    if (bytes < 1024) return `${bytes} B`;
    if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
    return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
  }
}

// Export singleton instance
export default new UploadService();
