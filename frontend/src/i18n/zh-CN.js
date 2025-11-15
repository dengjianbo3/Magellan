export default {
  // Common
  common: {
    save: '保存',
    cancel: '取消',
    delete: '删除',
    edit: '编辑',
    view: '查看',
    download: '下载',
    upload: '上传',
    share: '分享',
    search: '搜索',
    filter: '筛选',
    loading: '加载中...',
    noData: '暂无数据',
    confirm: '确认',
    back: '返回',
    next: '下一步',
    previous: '上一步',
    finish: '完成',
    close: '关闭',
    settings: '设置',
    logout: '退出登录'
  },

  // Sidebar
  sidebar: {
    dashboard: '仪表盘',
    reports: '报告',
    analysis: '分析',
    roundtable: '圆桌讨论',
    agents: 'AI 智能体',
    knowledge: '知识库',
    settings: '设置',
    collapse: '收起',
    startNewAnalysis: '开始新分析'
  },

  // Dashboard
  dashboard: {
    title: '仪表盘概览',
    welcome: '欢迎回来！以下是您的投资分析概况。',
    exportReport: '导出报告',

    stats: {
      totalReports: '总报告数',
      activeAnalyses: '进行中分析',
      aiAgents: 'AI 智能体',
      successRate: '成功率'
    },

    analysisTrends: '分析趋势',
    agentPerformance: '智能体性能',
    recentReports: '最近报告',
    viewAll: '查看全部',
    quickActions: '快速操作',
    activeAgents: '活跃 AI 智能体',

    timeRanges: {
      last7Days: '最近 7 天',
      last30Days: '最近 30 天',
      last3Months: '最近 3 个月',
      thisMonth: '本月',
      lastMonth: '上月',
      allTime: '全部时间'
    },

    chartLabels: {
      reportsGenerated: '生成报告',
      analysesStarted: '启动分析'
    },

    quickActionItems: {
      newAnalysis: {
        title: '新建分析',
        description: '开始新的项目分析'
      },
      uploadData: {
        title: '上传数据',
        description: '导入数据到知识库'
      },
      configureAgent: {
        title: '配置智能体',
        description: '设置新的 AI 智能体'
      },
      viewReports: {
        title: '查看报告',
        description: '浏览所有生成的报告'
      }
    },

    agentStatus: {
      active: '活跃',
      idle: '空闲',
      tasks: '个任务'
    }
  },

  // Analysis Wizard
  analysis: {
    title: '开始新分析',
    subtitle: '按照以下步骤配置您的投资分析项目',

    steps: {
      projectInfo: {
        title: '项目信息',
        description: '基本详情'
      },
      selectAgents: {
        title: '选择智能体',
        description: '选择 AI 智能体'
      },
      configure: {
        title: '配置',
        description: '数据与设置'
      }
    },

    step1: {
      title: '项目信息',
      projectName: '项目名称',
      projectNamePlaceholder: '例如：特斯拉 2024 Q4 投资分析',
      company: '公司/目标',
      companyPlaceholder: '例如：特斯拉公司',
      analysisType: '分析类型',
      description: '项目描述',
      descriptionPlaceholder: '提供关于此分析项目的额外背景信息...',
      required: '必填',

      types: {
        dueDiligence: {
          name: '尽职调查',
          description: '全面的投资分析'
        },
        marketAnalysis: {
          name: '市场分析',
          description: '市场趋势和定位'
        },
        financialReview: {
          name: '财务审查',
          description: '财务健康状况评估'
        },
        competitiveAnalysis: {
          name: '竞争分析',
          description: '竞争格局审查'
        }
      }
    },

    step2: {
      title: '选择 AI 智能体',
      subtitle: '选择应参与此分析的 AI 智能体',
      agentsParticipating: '个智能体参与',

      agents: {
        marketAnalyst: {
          name: '市场分析师',
          role: '市场情报',
          description: '分析市场趋势、竞争和行业动态',
          speed: '快速',
          expertise: '市场研究'
        },
        financialExpert: {
          name: '财务专家',
          role: '财务分析',
          description: '审查财务报表、比率和估值',
          speed: '中等',
          expertise: '金融与会计'
        },
        teamEvaluator: {
          name: '团队评估师',
          role: '团队评估',
          description: '评估管理团队、文化和组织结构',
          speed: '中等',
          expertise: '人力资源与领导力'
        },
        riskAssessor: {
          name: '风险评估师',
          role: '风险管理',
          description: '识别和分析潜在风险及挑战',
          speed: '快速',
          expertise: '风险分析'
        },
        techSpecialist: {
          name: '技术专家',
          role: '技术审查',
          description: '评估技术栈、创新和技术能力',
          speed: '较慢',
          expertise: '技术'
        },
        legalAdvisor: {
          name: '法律顾问',
          role: '法律合规',
          description: '审查法律结构、合规和监管问题',
          speed: '较慢',
          expertise: '法律与合规'
        }
      }
    },

    step3: {
      title: '数据源与配置',
      dataSources: '数据源',
      uploadDocuments: '上传额外文档',
      uploadPrompt: '点击上传或拖拽文件',
      uploadHint: 'PDF、DOCX、XLSX、CSV（最大 50MB）',
      analysisPriority: '分析优先级',

      sources: {
        financialReports: {
          name: '财务报告',
          description: '年报、10-K、10-Q 文件',
          status: '可用'
        },
        marketData: {
          name: '市场数据',
          description: '股价、市值、交易量',
          status: '实时'
        },
        newsSentiment: {
          name: '新闻与情绪',
          description: '新闻文章、社交媒体情绪',
          status: '可用'
        },
        companyData: {
          name: '公司数据库',
          description: '公司档案、行业数据',
          status: '可用'
        }
      },

      priorities: {
        low: {
          name: '低优先级',
          time: '3-5 天'
        },
        normal: {
          name: '正常',
          time: '1-2 天'
        },
        high: {
          name: '高优先级',
          time: '< 24 小时'
        }
      }
    },

    buttons: {
      previous: '上一步',
      next: '下一步',
      cancel: '取消',
      startAnalysis: '开始分析'
    }
  },

  // Agent Chat
  agentChat: {
    activeAgents: '活跃智能体',
    agentsParticipating: '个智能体参与',
    pauseAll: '暂停全部智能体',
    exportDiscussion: '导出讨论',

    status: {
      inProgress: '进行中',
      completed: '已完成',
      paused: '已暂停'
    },

    started: '开始于',
    isThinking: '正在思考...',

    sendMessage: '发送',
    inputPlaceholder: '提问或提供额外背景信息...',
    ctrlEnterHint: '按 Ctrl+Enter 发送',

    analysisProgress: '分析进度',
    overallProgress: '整体进度',
    keyInsights: '关键洞察',
    quickActions: '快速操作',

    insights: {
      by: '来自'
    },

    actions: {
      viewRawData: '查看原始数据',
      generateReport: '生成报告',
      shareAnalysis: '分享分析'
    },

    tasks: {
      marketAnalysis: '市场分析',
      financialReview: '财务审查',
      riskAssessment: '风险评估',
      teamEvaluation: '团队评估',
      techAssessment: '技术评估',
      finalReport: '最终报告'
    },

    taskStatus: {
      completed: '已完成',
      inProgress: '进行中',
      pending: '待处理'
    }
  },

  // Reports
  reports: {
    title: '报告',
    subtitle: '管理和查看所有生成的分析报告',
    newReport: '新建报告',

    filters: {
      allTypes: '全部类型',
      allStatus: '全部状态',
      dueDiligence: '尽职调查',
      marketAnalysis: '市场分析',
      financialReview: '财务审查',
      completed: '已完成',
      inProgress: '进行中',
      draft: '草稿'
    },

    searchPlaceholder: '搜索报告...',

    card: {
      agents: '个智能体',
      view: '查看',
      download: '下载',
      share: '分享'
    },

    status: {
      completed: '已完成',
      inProgress: '进行中',
      draft: '草稿'
    }
  },

  // AI Agents
  agents: {
    title: 'AI 智能体',
    subtitle: '配置和管理您的 AI 分析智能体',
    createCustomAgent: '创建自定义智能体',

    card: {
      analyses: '分析次数',
      avgResponse: '平均响应',
      capabilities: '能力',
      configure: '配置',
      pause: '暂停',
      activate: '激活'
    },

    configModal: {
      title: '配置智能体',
      agentName: '智能体名称',
      aiModel: 'AI 模型',
      temperature: '温度',
      temperatureHint: {
        precise: '精确',
        creative: '创造性'
      },
      systemPrompt: '系统提示词',
      maxTokens: '最大令牌数',
      saveChanges: '保存更改',
      cancel: '取消',

      models: {
        gpt4: 'GPT-4（最准确）',
        gpt35: 'GPT-3.5（平衡）',
        claude2: 'Claude 2（长上下文）'
      }
    }
  },

  // Knowledge Base
  knowledge: {
    title: '知识库',
    documentsCount: '篇文档',
    searchPlaceholder: '搜索文档...',
    upload: '上传',
    newCategory: '新建分类',

    categories: {
      all: '全部文档',
      financial: '财务报告',
      market: '市场研究',
      legal: '法律文档',
      other: '其他'
    },

    table: {
      name: '名称',
      type: '类型',
      size: '大小',
      uploaded: '上传时间',
      status: '状态',
      actions: '操作'
    },

    status: {
      processed: '已处理',
      processing: '处理中',
      failed: '失败'
    },

    empty: {
      title: '未找到文档',
      subtitle: '上传文档以开始',
      uploadButton: '上传文档'
    },

    uploadModal: {
      title: '上传文档',
      category: '分类',
      files: '文件',
      uploadPrompt: '点击上传或拖拽文件',
      uploadHint: 'PDF、DOCX、XLSX、CSV、TXT（最大 100MB）',
      upload: '上传',
      file: '个文件',
      files: '个文件',
      cancel: '取消'
    }
  },

  // Settings
  settings: {
    title: '设置',
    subtitle: '管理您的账户和应用偏好设置',

    sections: {
      profile: '个人资料',
      notifications: '通知',
      security: '安全',
      api: 'API 密钥',
      appearance: '外观'
    },

    profile: {
      title: '个人资料设置',
      changeAvatar: '更换头像',
      firstName: '名',
      lastName: '姓',
      email: '邮箱',
      role: '角色',
      saveChanges: '保存更改'
    },

    notifications: {
      title: '通知偏好设置',
      analysisComplete: {
        title: '分析完成',
        description: '分析完成时接收通知'
      },
      agentUpdates: {
        title: '智能体更新',
        description: '智能体状态变化通知'
      },
      weeklyReports: {
        title: '周报',
        description: '接收每周活动摘要'
      },
      emailNotifications: {
        title: '邮件通知',
        description: '将通知发送到邮箱'
      }
    },

    security: {
      title: '安全设置',
      changePassword: '修改密码',
      currentPassword: '当前密码',
      newPassword: '新密码',
      confirmPassword: '确认新密码',
      updatePassword: '更新密码',
      twoFactorAuth: '双因素认证',
      enable2FA: {
        title: '启用 2FA',
        description: '增加额外的安全层',
        button: '启用'
      }
    },

    api: {
      title: 'API 配置',
      openaiKey: 'OpenAI API 密钥',
      claudeKey: 'Claude API 密钥',
      update: '更新',
      usage: 'API 用量',
      thisMonth: '本月'
    },

    appearance: {
      title: '外观',
      theme: '主题',
      themes: {
        light: '浅色',
        dark: '深色',
        auto: '自动'
      },
      language: '语言',
      languages: {
        zhCN: '简体中文',
        en: 'English',
        zhTW: '繁體中文'
      }
    }
  },

  // Roundtable Discussion
  roundtable: {
    title: '圆桌讨论',
    subtitle: '多位投资专家针对同一问题进行深度讨论分析',

    startPanel: {
      title: '启动新的圆桌讨论',
      topicLabel: '讨论主题',
      topicPlaceholder: '例如: 特斯拉 2024 Q4 的投资价值分析',
      expertsLabel: '参与专家',
      expertsSelected: '已选择',
      roundsLabel: '讨论轮数',
      rounds: '轮',
      startButton: '开始讨论',
      required: '必填'
    },

    experts: {
      leader: {
        name: 'Leader (领导者)',
        role: '讨论主持人',
        description: '主持讨论,综合各方观点,形成最终结论'
      },
      marketAnalyst: {
        name: 'Market Analyst (市场分析师)',
        role: '市场研究',
        description: '分析市场趋势、竞争态势和行业动态'
      },
      financialExpert: {
        name: 'Financial Expert (财务专家)',
        role: '财务分析',
        description: '评估财务报表、估值和财务健康度'
      },
      teamEvaluator: {
        name: 'Team Evaluator (团队评估)',
        role: '团队分析',
        description: '评估管理团队、组织文化和执行能力'
      },
      riskAssessor: {
        name: 'Risk Assessor (风险评估)',
        role: '风险管理',
        description: '识别和分析潜在风险与挑战'
      }
    },

    discussion: {
      progress: '讨论进度',
      currentRound: '当前轮数',
      messageCount: '消息数量',
      participants: '参与专家',
      stopButton: '停止讨论',
      exportButton: '导出结果',
      status: {
        running: '进行中',
        completed: '已完成'
      },
      startedAt: '开始于',
      connecting: '正在连接到圆桌讨论...'
    },

    summary: {
      title: '讨论总结',
      completed: '圆桌讨论已完成'
    }
  }
};
