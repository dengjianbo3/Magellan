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
    logout: '退出登录',
    pleaseSelect: '请选择',
    clickToUpload: '点击上传',
    submitting: '提交中...',
    starting: '启动中...',
    min: '分',
    sec: '秒',
    optional: '可选'
  },

  // Authentication
  auth: {
    // Login
    loginTitle: '登录您的账户',
    loginSubtitle: '欢迎回到 Magellan 投资分析平台',
    email: '邮箱',
    emailPlaceholder: '请输入您的邮箱',
    password: '密码',
    passwordPlaceholder: '请输入密码',
    rememberMe: '记住我',
    forgotPassword: '忘记密码？',
    login: '登录',
    loggingIn: '登录中...',
    noAccount: '还没有账户？',
    registerNow: '立即注册',

    // Register
    registerTitle: '创建新账户',
    registerSubtitle: '加入 Magellan，开启智能投资分析',
    name: '姓名',
    namePlaceholder: '请输入您的姓名',
    organization: '所属机构',
    organizationPlaceholder: '请输入您的机构名称',
    newPasswordPlaceholder: '请输入新密码',
    confirmPassword: '确认密码',
    confirmPasswordPlaceholder: '请再次输入密码',
    passwordRequirements: '密码至少8位，包含大小写字母和数字',
    passwordMismatch: '两次输入的密码不一致',
    acceptTerms: '我已阅读并同意',
    termsOfService: '服务条款',
    and: '和',
    privacyPolicy: '隐私政策',
    register: '注册',
    registering: '注册中...',
    hasAccount: '已有账户？',
    loginNow: '立即登录',

    // Errors
    loginFailed: '登录失败，请检查邮箱和密码',
    registerFailed: '注册失败，请稍后重试',
    sessionExpired: '会话已过期，请重新登录',
    unauthorized: '未授权访问，请先登录'
  },

  // Validation
  validation: {
    required: '此字段为必填项',
    minLength: '最少需要 {n} 个字符',
    maxLength: '最多 {n} 个字符',
    min: '最小值为 {n}',
    max: '最大值为 {n}',
    pattern: '格式不正确'
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
    startNewAnalysis: '开始新分析',
    brandSubtitle: 'AI 投资分析'
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
    },

    hitl: {
      requiredTitle: '初步分析完成，请审核',
      keyQuestions: '关键尽职调查问题',
      answerPlaceholder: '在此输入您的答案或备注...',
      actionRequired: '需要操作：请选择一个选项'
    },

    report: {
      preliminaryMemo: '初步投资备忘录',
      companyInfo: '公司信息',
      name: '名称',
      industry: '行业',
      stage: '阶段',
      teamAssessment: '团队评估',
      teamAnalysisCompleted: '团队分析已完成。',
      marketAnalysis: '市场分析',
      marketAnalysisCompleted: '市场分析已完成。',
      savedSuccess: '分析成功完成！',
      saveButton: '保存分析报告',
      savedButton: '报告已保存',
      viewFull: '查看完整报告'
    },

    sidebar: {
      elapsedTime: '已用时间',
      estRemaining: '预计剩余',
      currentAction: '当前操作',
      processing: '处理中...',
      configuration: '配置信息',
      company: '公司',
      type: '类型',
      agents: '智能体',
      active: '活跃'
    }
  },

  // Scenarios (Mock Data Fallback)
  scenarios: {
    earlyStage: {
      name: '早期风险投资',
      description: '分析天使轮/种子轮初创公司，重点关注团队和市场潜力。'
    },
    growth: {
      name: '成长期权益投资',
      description: '评估具有既定指标和单位经济效益的规模化公司。'
    },
    publicMarket: {
      name: '公开市场',
      description: '对上市证券和报告进行全面分析。'
    },
    industryResearch: {
      name: '行业研究',
      description: '深入研究特定市场领域和竞争格局。'
    },
    alternative: {
      name: '另类资产',
      description: '房地产、加密货币和其他非传统资产类别。'
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
    },

    // Report detail view
    detail: {
      backToList: '返回列表',
      reportDetails: '报告详情',
      reportType: '报告类型',
      saveTime: '保存时间',
      sessionId: 'Session ID',

      // Roundtable specific
      meetingMinutes: '会议纪要',
      roundtableDiscussion: '圆桌讨论',
      participatingExperts: '参与专家',
      discussionHistory: '讨论历史记录',
      clickToExpand: '点击展开查看完整讨论过程',
      messages: '条消息',
      conclusionReason: '会议结束原因',
      discussionTopic: '讨论主题',
      discussionDuration: '讨论时长',

      // Analysis sections
      detailedAnalysis: '详细分析报告',
      investmentRecommendation: '投资建议',
      overallScore: '综合评分',
      executiveSummary: '执行摘要',
      keyFindings: '关键发现',
      highlights: '亮点',
      concerns: '关注点',
      score: '评分',
      swotAnalysis: 'SWOT 分析',
      strengths: '优势',
      weaknesses: '劣势',
      opportunities: '机会',
      threats: '威胁',
      nextSteps: '下一步行动建议',
      ddQuestions: '尽调问题',
      executionSteps: '执行步骤记录',
      dataVisualization: '数据可视化',
      refresh: '刷新',

      // Chart tabs
      financialAnalysis: '财务分析',
      marketAnalysis: '市场分析',
      teamAndRisk: '团队与风险',
      revenueTrend: '收入趋势',
      profitMarginTrend: '利润率趋势',
      marketShareDistribution: '市场份额分布',
      riskAssessmentMatrix: '风险评估矩阵',

      // Actions
      actions: '操作',
      exportPdf: '导出 PDF',
      exporting: '导出中...',
      shareReport: '分享报告',
      deleteReport: '删除报告',
      confirmDelete: '确认删除?',
      deleteWarning: '您即将删除报告',
      deleteIrreversible: '此操作无法撤销。',
      cancel: '取消',
      confirmDeleteBtn: '确认删除'
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
      title: 'AI 模型配置',
      llmProvider: 'LLM 提供商',
      llmProviderDesc: '选择用于 AI 分析的大语言模型提供商',
      providers: {
        gemini: 'Gemini (Google)',
        kimi: 'Kimi (Moonshot AI)'
      },
      currentModel: '当前模型',
      providerStatus: '状态',
      available: '可用',
      unavailable: '未配置',
      switching: '切换中...',
      switchSuccess: '已切换到 {provider}',
      switchError: '切换失败: {error}',
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

  // Analysis Wizard V2
  analysisWizard: {
    // Scenario Selection
    selectScenario: '选择投资场景',
    selectScenarioHint: '请选择最符合您投资需求的场景类型',
    loadingScenarios: '正在加载场景...',
    selected: '已选择',
    comingSoon: '即将推出',
    recommended: '推荐',
    na: '不适用',
    quickJudgment: '快速判断',
    standardAnalysis: '标准分析',
    nextStep: '下一步',

    // Analysis Config
    configAnalysis: '配置分析',
    configAnalysisHint: '选择分析深度和关注领域',
    configureIndustryAnalysis: '配置行业分析',
    configureIndustryAnalysisHint: '为您的 AI 驱动研究报告定义参数',
    analysisDepth: '分析深度',
    quickMode: '快速判断',
    standardMode: '标准分析',
    comprehensiveMode: '深度分析',
    timeframe: '时间范围',
    focusAreas: '重点关注领域',
    optional: '可选',
    reportLanguage: '报告语言',
    analysisSummary: '分析预览',
    depth: '深度',
    estimatedTime: '预计耗时',
    startAnalysis: '开始分析',

    // Config sections
    defineResearchScope: '定义研究范围',
    selectResearchMethodologies: '选择研究方法',
    setDataSourcePreferences: '设置数据源偏好',
    choosePredictiveModels: '选择预测模型',
    defineCompetitiveAnalysisFocus: '定义竞争分析重点',

    // Form fields
    industryTopic: '行业/主题',
    industryTopicLabel: '待分析的行业/主题',
    industryTopicPlaceholder: '例如: "全球电动汽车市场"',
    geography: '地理区域',
    geographyPlaceholder: '请选择地理区域',
    geographyGlobal: '全球',
    geographyNorthAmerica: '北美',
    geographyEurope: '欧洲',
    geographyAsiaPacific: '亚太地区',
    geographyChina: '中国',
    mainProducts: '主要产品/服务',
    mainProductsPlaceholder: '例如: GPU, TPU, AI加速器',
    marketSize: '市场规模 (十亿)',
    marketSizePlaceholder: '例如: 50',
    maxSize: '最大规模',
    maxSizePlaceholder: '例如: 200',
    keyCompetitors: '主要竞争对手',
    keyCompetitorsPlaceholder: '例如: Google (按回车添加多个竞争对手)',

    // Methodologies
    swotAnalysis: 'SWOT 分析',
    portersFiveForces: '波特五力分析',
    pestleAnalysis: 'PESTLE 分析',
    valueChainAnalysis: '价值链分析',

    // Hints
    selectDataSources: '选择要包含在分析中的数据源',
    selectPredictiveModels: '选择用于预测的 AI 模型',
    specifyCompetitiveParams: '指定竞争分析参数',

    // Actions
    saveAsTemplate: '保存为模板',
    generateReport: '生成报告',

    // Early Stage Input
    earlyStageInvestment: '早期投资分析',
    earlyStageHint: '请提供项目的基本信息,我们将进行专业分析',
    companyName: '公司名称',
    companyNamePlaceholder: '请输入公司名称',
    fundingStage: '融资阶段',
    selectStage: '请选择融资阶段',
    industry: '所属行业',
    industryPlaceholder: '例如: 人工智能、企业服务',
    businessPlan: '商业计划书',
    uploadFile: '上传文件',
    changeFile: '更换文件',
    uploading: '上传中',
    uploadFailed: '上传失败',
    bpHint: '支持 PDF、PPT、Word 格式',
    foundedYear: '成立年份',
    foundedYearPlaceholder: '请输入成立年份',
    teamMembers: '团队成员',
    teamMembersPlaceholder: '每行一个成员,格式: 姓名, 职位, 背景\n例如:\n张三, CEO, 前阿里巴巴P9\n李四, CTO, 清华博士',
    teamMembersHint: '可以简单描述核心团队成员的背景',

    // Analysis Progress
    analyzing: '分析中',
    analysisFor: '分析目标',
    analyzingHint: '分析中... 系统正在处理实时市场数据。',
    cancelAnalysis: '取消分析',
    overallProgress: '整体进度',
    estimatedTimeRemaining: '预计剩余时间',
    agentsActive: '活跃智能体',
    analysisStarted: '分析开始时间',
    aiAgentStatus: 'AI 智能体状态',
    analysisTimeline: '分析时间线',
    elapsedTime: '已用时间',
    completed: '已完成',
    completedStatus: '已完成',
    running: '运行中',
    runningStatus: '运行中',
    queued: '排队中',
    inProgress: '进行中',
    pending: '待处理',

    // Agent messages
    dataCollectionAgent: '数据采集智能体',
    completedFetched: '已完成: 获取实时市场数据。',
    financialModelingAgent: '财务建模智能体',
    runningAnalyzing: '运行中: 分析财务报表...',
    valuationAgent: '估值智能体',
    runningGenerating: '运行中: 生成估值模型...',
    riskAssessmentAgent: '风险评估智能体',
    queuedStatus: '排队中',

    // Timeline events
    fetchingMarketData: '获取市场数据',
    analyzingFinancialStatements: '分析财务报表',
    generatingValuationModels: '生成估值模型',
    finalReportCompilation: '最终报告编制',

    quickJudgmentResult: '快速判断结果',
    recommendation: '投资建议',
    overallScore: '综合评分',
    scores: '评分',
    verdict: '结论',
    advantages: '优势',
    concerns: '关注点',
    nextSteps: '下一步建议',
    upgradeToStandard: '升级为标准分析',
    exportReport: '导出报告',
    viewFullReport: '查看完整报告',
    analysisCompleted: '分析完成',
    analysisCompletedHint: '您可以查看完整的分析报告',

    // Progress Steps
    workflowStarted: '工作流已启动',
    stepInProgress: '进行中',
    stepCompleted: '已完成',
    connectingWebSocket: '正在连接实时通道...',
    waitingForResults: '等待分析结果...',

    // Connection Status
    reconnecting: '正在重新连接...',
    connectionLost: '连接已断开，请检查网络',
    connectionRestored: '连接已恢复',
    unknownError: '未知错误',
    analysisError: '分析过程中发生错误',
    analysisTimeout: '分析超时，请重试',

    // Wizard Steps
    inputTarget: '输入目标',
    targetInfo: '目标信息',
    configTitle: '配置分析参数',
    configSubtitle: '选择分析模式和关注领域',
    targetSummary: '目标摘要',
    analysisSettings: '分析设置',
    quickModeDesc: '4-6分钟快速评估，适合初步筛选',
    standardModeDesc: '12-20分钟深度分析，提供完整报告',
    analysisFocus: '分析重点',
    analysisFocusHint: '选择您最关注的分析维度（可多选）',
    additionalOptions: '附加选项',
    includeComparison: '包含同行对比分析',
    includeRisks: '包含风险评估',
    detailedFinancials: '详细财务建模',
    mockDataWarning: '⚠️ 后端服务不可用，当前显示演示数据',
    mockDataHint: '请启动后端服务以使用真实分析功能',
    error: '错误',
    almostDone: '即将完成',

    // Step Result Card
    tam: 'TAM',
    sam: 'SAM',
    growthRate: '增长率',
    marketMaturity: '成熟度',
    score: '分',
    topPlayers: '头部玩家',
    marketConcentration: '集中度',
    entryBarriers: '进入壁垒',
    keyTrends: '关键趋势',
    techDirection: '技术方向',
    policySupport: '政策支持',
    investmentOpportunities: '投资机会',
    subSectors: '细分赛道',
    revenueAssessment: '收入评估',
    cashFlow: '现金流',
    profitability: '盈利能力',
    concernsLabel: '关注点',
    valuationLevel: '估值水平',
    peRatio: 'PE比率',
    priceTarget: '目标价格',

    // Time units
    minutes: '分',
    seconds: '秒',
    minute: '分钟',
    second: '秒',

    // Recommendations
    recommendationBuy: '建议投资',
    recommendationPass: '建议观望',
    recommendationFurtherDD: '需要深入研究',
    recommendationInvest: '建议投资',

    // Alerts
    upgradeFeatureInDevelopment: '升级到标准分析功能开发中...',
    exportFeatureInDevelopment: '导出报告功能开发中...',

    // Session Recovery
    sessionRecovery: '检测到未完成的分析',
    sessionRecoveryDesc: '您有一个进行中的分析任务，是否要继续？',
    projectName: '项目名称',
    scenario: '分析场景',
    startedAt: '开始时间',
    startNew: '开始新分析',
    continueSession: '继续分析',
    sessionNotFound: '会话不存在',

    // Errors
    analysisError: '分析错误',
    unknownError: '未知错误',
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
    },

    // Human-in-the-Loop (HITL)
    hitl: {
      interruptButton: '打断并补充',
      dialogTitle: '打断并补充信息',
      respondingTo: '您正在回应:',
      inputLabel: '补充信息',
      inputPlaceholder: '请输入您的补充信息，例如：\n- 纠正专家的错误分析\n- 补充重要的背景信息\n- 提出新的关注点\n- 提供内部数据或情况\n\nLeader会根据您的补充重新规划讨论方向。',
      inputHint: '提示：您的补充会被发送给所有专家，Leader会根据这个信息调整讨论方向',
      submit: '发送补充',
      submitting: '发送中...',
      cancel: '取消',
      interventionSent: '补充信息已发送，Leader将根据您的信息重新规划讨论',
      interventionError: '发送补充信息失败'
    }
  },

  // Early Stage Investment
  earlyStage: {
    // Progress Steps
    selectScenario: '选择投资场景',
    inputTarget: '输入目标',
    configAnalysis: '配置分析',
    analyzing: '分析中',

    // Input Target
    title: '早期投资分析',
    subtitle: '分析天使轮、种子轮、Pre-A和A轮公司,重点关注团队背景、市场机会和产品创新',
    companyName: '公司名称',
    companyNamePlaceholder: '例如: XX科技',
    companyNameHint: '请输入待分析的公司名称',
    fundingStage: '融资阶段',
    selectStage: '请选择融资阶段',
    industry: '所属行业',
    industryPlaceholder: '例如: 人工智能、新能源汽车',
    businessPlan: '商业计划书 (可选)',
    clickToUpload: '点击上传文件',
    supportedFormats: '支持 PDF, PPT, Word 格式',
    uploadError: '文件上传失败',
    foundedYear: '成立年份',
    foundedYearPlaceholder: '例如: 2023',
    teamMembers: '团队成员',
    teamMembersPlaceholder: '每行一个成员,格式: 姓名, 职位, 背景\n例如:\n张三, CEO, 前阿里巴巴技术总监\n李四, CTO, 斯坦福大学博士',
    teamMembersHint: '每行输入一位团队成员信息,逗号分隔',
    uploading: '上传中',
    back: '返回',
    next: '下一步',

    // Config Analysis
    configTitle: '配置早期投资分析',
    configSubtitle: '定义分析参数以生成您的投资报告',
    projectName: '项目/分析名称',
    projectNamePlaceholder: '输入项目或公司名称',
    selectDataSources: '选择数据源',
    publicMarketData: '公开市场数据',
    paidIndustryReports: '付费行业报告',
    internalKnowledge: '内部知识库',
    newsSocial: '新闻与社交媒体',
    definePriorities: '定义分析优先级',
    teamFounder: '团队与创始人背景',
    technologyProduct: '技术与产品',
    marketSizeTAM: '市场规模与TAM/SOM',
    competitiveLandscape: '竞争格局',
    setRiskAppetite: '设置风险偏好',
    aggressive: '激进型',
    aggressiveDesc: '高风险高回报',
    balanced: '平衡型',
    balancedDesc: '适度增长',
    conservative: '保守型',
    conservativeDesc: '稳健增长',
    reset: '重置',
    generateReport: '生成报告',

    // Agents
    teamEvaluationAgent: '团队评估智能体',
    analyzingTeamBackground: '正在分析团队背景...',
    marketAnalysisAgent: '市场分析智能体',
    analyzingMarketSize: '正在分析市场规模...',
    riskAssessmentAgent: '风险评估智能体',
    scanningRedFlags: '正在扫描风险标志...'
  },

  // Growth Stage Investment
  growthStage: {
    // Input Target
    title: '成长期投资分析',
    subtitle: '分析B轮至Pre-IPO公司，重点关注财务健康、增长潜力和市场地位',
    basicInfo: '基本信息',
    companyName: '公司名称',
    companyNamePlaceholder: '例如: XX科技',
    tickerSymbol: '股票代码（可选）',
    tickerSymbolPlaceholder: '例如: AAPL',
    industrySector: '行业/领域（可选）',
    industrySectorPlaceholder: '例如: 企业服务',
    headquarters: '总部位置（可选）',
    headquartersPlaceholder: '例如: 北京',
    fundingStage: '融资阶段',
    seriesB: 'B轮',
    seriesC: 'C轮',
    seriesD: 'D轮',
    seriesE: 'E轮',
    preIPO: 'Pre-IPO',
    financialData: '财务数据',
    financialDataHint: '上传财务报表、年报或审计报告，帮助我们更准确地评估公司的财务健康状况',
    clickToUpload: '点击上传文件',
    dragAndDrop: '或拖拽文件到此处',
    supportedFormats: '支持 CSV, XLSX, PDF 格式',
    marketPositioning: '市场定位与策略',
    coreProducts: '核心产品/服务',
    coreProductsPlaceholder: '请简要描述公司的核心产品或服务...',
    competitiveLandscape: '竞争格局',
    competitorName: '竞争对手名称',
    marketShare: '市场份额 (%)',
    addCompetitor: '添加竞争对手',

    // Config Analysis
    configTitle: '配置成长期投资分析',
    configSubtitle: '设置详细参数以进行长期投资分析',
    growthModelSelection: '增长模型选择 (Growth Model Selection)',
    sCurveGrowth: 'S曲线增长',
    sCurveGrowthDesc: '模拟最初呈指数增长，然后随着达到饱和而放缓的增长',
    linearGrowth: '线性增长',
    linearGrowthDesc: '模拟已经稳定、恒定的增长率随时间变化',
    exponentialGrowth: '指数增长',
    exponentialGrowthDesc: '模拟加速增长，增长率本身随时间增加',
    pleaseSelectGrowthModel: '请选择增长模型',

    competitionAnalysisFocus: '竞争分析调整 (Competition Analysis Focus)',
    competitiveAdvantages: '竞争优势',
    technologyLeadership: '技术领先',
    brandRecognition: '品牌认知',
    networkEffects: '网络效应',
    costAdvantage: '成本优势',
    dataAdvantage: '数据优势',
    competitionIntensity: '竞争强度',
    lowCompetition: '低竞争',
    mediumCompetition: '中等竞争',
    highCompetition: '高竞争',

    marketOutlookAssessment: '市场前景评估 (Market Outlook Assessment)',
    marketGrowthRate: '市场增长率',
    marketGrowthRateHint: '预期的年度市场增长率 (CAGR)',
    marketMaturity: '市场成熟度',
    emergingMarket: '新兴市场',
    growingMarket: '成长市场',
    matureMarket: '成熟市场',
    keyMarketDrivers: '关键市场驱动因素',
    keyMarketDriversPlaceholder: '描述推动市场增长的关键因素...',

    financialProjections: '财务预测参数 (Financial Projections)',
    projectionPeriod: '预测周期',
    threeYears: '3年',
    fiveYears: '5年',
    tenYears: '10年',
    revenueGrowthAssumption: '收入增长假设',
    profitMarginTarget: '利润率目标',
    burnRateAssumption: '烧钱率假设',
    monthlyBurnRate: '每月烧钱率',
    keyFinancialMetrics: '关键财务指标',
    revenue: '收入',
    grossMargin: '毛利率',
    operatingMargin: '营业利润率',
    netIncome: '净利润',
    cashFlow: '现金流',
    cac: '获客成本 (CAC)',
    ltv: '客户终身价值 (LTV)',
    runway: '资金跑道',

    // Agents
    financialHealthAgent: '财务健康智能体',
    analyzingFinancialHealth: '正在分析财务健康状况...',
    growthPotentialAgent: '增长潜力智能体',
    assessingGrowthPotential: '正在评估增长潜力...',
    marketPositionAgent: '市场地位智能体',
    analyzingMarketPosition: '正在分析市场地位...'
  },

  // Public Market Investment
  publicMarket: {
    // Input Target
    title: '公开市场投资分析',
    subtitle: '分析上市公司股票、ETF或指数，重点关注估值、基本面、技术面和市场情绪',
    targetCompany: '目标公司',
    tickerOrName: '输入公司股票代码或名称',
    searchPlaceholder: '搜索AAPL或Apple Inc.',
    tickerHint: '输入股票代码(如AAPL)或公司名称进行搜索',
    tickerRequired: '请输入股票代码',

    selectResearchPeriod: '选择研究周期',
    quarterly: '季度',
    annually: '年度',
    customRange: '自定义范围',
    startDate: '开始日期',
    endDate: '结束日期',
    customRangeRequired: '请选择自定义日期范围',

    chooseKeyMetrics: '选择关键指标',
    peRatio: 'PE 市盈率',
    priceToSales: 'Price-to-Sales 市销率',
    roe: 'ROE 净资产收益率',
    debtToEquity: 'Debt-to-Equity 资产负债率',
    ebitdaMargin: 'EBITDA Margin EBITDA利润率',
    addMetric: '添加指标',
    enterCustomMetric: '请输入自定义指标名称',

    uploadFilings: '上传财报或研究报告',
    clickToUpload: '点击上传或拖拽文件到此处',
    uploadHint: 'SEC财报、研究报告或其他相关文档',

    // Config Analysis
    allocationAnalysis: '配置分析',
    configureParameters: '配置公开市场投资分析的详细参数',
    generateReport: '生成报告',

    configureDataSources: '配置数据源',
    realTimeQuotes: '实时行情数据',
    financialFilings: '财务报表',
    timePeriod: '时间周期',
    newsSocialMedia: '新闻与社交媒体',
    selectAtLeastOneDataSource: '请至少选择一个数据源',

    defineAgentFocus: '定义AI智能体焦点',
    weight: '权重',
    sentimentAnalysis: '情绪分析',
    quantitativeStrategy: '量化策略',
    fundamentalAnalysis: '基本面分析',
    technicalIndicators: '技术指标',

    setRiskParameters: '设置风险参数',
    riskAppetite: '风险偏好',
    conservative: '保守型',
    moderate: '平衡型',
    aggressive: '激进型',
    maxDrawdown: '最大回撤 (%)',
    targetReturn: '目标回报 (%)',
    timeHorizon: '投资期限',
    shortTerm: '短期',
    mediumTerm: '中期',
    longTerm: '长期'
  },

  // Alternative Investment
  alternative: {
    title: '另类投资分析',
    subtitle: '分析加密货币、DeFi、NFT等另类投资标的，关注技术基础、代币经济学、社区活跃度',

    // Input form
    projectOverview: '项目概览',
    projectOverviewDesc: '提供关于项目的基本信息',
    assetClass: '资产类别',
    selectAssetClass: '选择资产类别',
    crypto: '加密货币',
    defi: 'DeFi 去中心化金融',
    nft: 'NFT 数字藏品',
    web3: 'Web3 应用',
    projectName: '项目名称',
    projectNamePlaceholder: '例如: Bitcoin, Uniswap, Bored Ape...',
    investmentSize: '投资规模',
    investmentSizePlaceholder: '请输入投资金额',

    documentation: '尽职调查文档',
    documentationDesc: '上传项目白皮书、审计报告等资料',
    uploadDocs: '上传文档',
    uploadHint: '点击或拖拽文件到此处上传',
    supportedFormats: '支持 PDF, DOC, DOCX, TXT 格式',

    keyStakeholders: '关键利益相关方',
    stakeholdersDesc: '项目核心团队成员信息',
    name: '姓名',
    namePlaceholder: '成员姓名',
    role: '职位',
    rolePlaceholder: '职位/角色',
    addMember: '添加成员',
    removeMember: '删除成员',

    analysisDirectives: '分析指令',
    directivesDesc: '您想重点关注的问题或分析方向',
    directivesPlaceholder: '例如:\n- 评估项目的技术创新性\n- 分析代币经济模型的可持续性\n- 社区治理机制的有效性\n- 竞争格局和市场定位',

    riskWarning: '投资风险提示',
    riskWarningText: '另类投资具有高风险性,请谨慎评估。建议仅投资您能承受损失的资金。',

    // Config form
    allocationAnalysis: '配置分析',
    configSubtitle: '配置您的另类投资分析报告参数',

    valuationModel: '估值模型',
    dcf: 'DCF 现金流折现',
    dcfTitle: '现金流折现模型',
    dcfDesc: '通过预测项目未来现金流并折现到现值来评估价值。适合有稳定收益预期的DeFi协议或NFT平台。',
    comparableCompany: '可比公司分析',
    comparableTitle: '可比公司分析',
    comparableDesc: '通过对比同类项目的估值指标(如TVL/市值比、用户数等)来评估目标项目。适合已有多个竞品的成熟赛道。',
    precedentTransactions: '先例交易法',
    precedentTitle: '先例交易法',
    precedentDesc: '参考类似项目的历史融资或收购价格来估值。适合有充足并购案例的细分领域。',
    moreInfo: '更多信息',

    dueDiligenceFocus: '尽调关注点',
    legalCompliance: '法律与合规',
    operationalRisk: '运营风险',
    financialIntegrity: '财务报表完整性',
    marketCompetition: '市场竞争',

    exitStrategyPreference: '退出策略偏好',
    ipo: 'IPO',
    strategicAcquisition: '战略收购 (M&A)',
    ipoPreferred: '偏好 IPO 退出',
    acquisitionPreferred: '偏好并购退出',
    balancedExit: '兼顾多种退出方式',

    analysisDepth: '分析深度',
    quickAnalysis: '快速分析',
    standardAnalysis: '标准分析',
    deepAnalysis: '深度分析',

    riskTolerance: '风险承受能力',
    conservative: '保守型',
    moderate: '稳健型',
    aggressive: '进取型',

    resetToDefault: '重置为默认',
    generateReport: '生成报告',

    // Agents
    techFoundationAgent: '技术基础智能体',
    analyzingTechFoundation: '正在分析技术架构和安全性...',
    tokenomicsAgent: '代币经济学智能体',
    analyzingTokenomics: '正在分析代币模型和经济机制...',
    communityAgent: '社区活跃度智能体',
    analyzingCommunity: '正在分析社区参与度和治理...',

    // Validation
    assetClassRequired: '请选择资产类别',
    projectNameRequired: '请输入项目名称',
    investmentSizeRequired: '请输入投资规模',
    investmentSizePositive: '投资规模必须大于0'
  },

  // Industry Research
  industryResearch: {
    title: '行业研究分析',
    subtitle: '系统性分析行业趋势、竞争格局、投资机会和风险因素',

    // Input page
    defineTarget: '定义您的研究目标',
    defineTargetDesc: '提供关于您想要分析的行业或市场的基本信息',
    industryName: '行业名称',
    industryPlaceholder: '例如: 人工智能芯片',
    researchScope: '研究范围',
    selectScope: '请选择一个或多个区域',
    global: '全球',
    china: '中国',
    us: '美国',
    europe: '欧洲',
    asia: '亚太',
    mainProducts: '主要产品/服务',
    mainProductsPlaceholder: '例如: GPU, TPU, AI加速器',
    marketSize: '市场规模 (十亿元)',
    marketSizePlaceholder: '例如: 50',
    billionYuan: '十亿元',
    maxRegions: '最大规模',
    maxRegionsPlaceholder: '例如: 200',
    keyParticipants: '关键参与者',
    participantPlaceholder: '例如: Google (输入后按回车键)',
    participantHint: '输入公司名称并按回车键添加标签',
    startAnalysis: '开始分析',
    industryNameRequired: '请输入行业名称',
    marketResearch: '市场研究',

    // Config page
    configureAnalysis: 'Configure Industry Analysis',
    configureAnalysisDesc: 'Define the parameters for your AI-driven research report',
    defineResearchScope: 'Define Your Research Scope',
    industryTopicAnalyze: 'Industry/Topic to Analyze',
    researchScopePlaceholder: 'e.g., Global Electric Vehicle Market',

    selectMethodologies: 'Select Research Methodologies',
    swotAnalysis: 'SWOT Analysis',
    portersFiveForces: "Porter's Five Forces",
    pestleAnalysis: 'PESTLE Analysis',
    valueChainAnalysis: 'Value Chain Analysis',

    setDataSources: 'Set Data Source Preferences',
    industryReports: 'Industry Reports',
    marketResearch: 'Market Research',
    financialData: 'Financial Data',
    newsMedia: 'News & Media',
    expertInterviews: 'Expert Interviews',
    companyFilings: 'Company Filings',

    choosePredictiveModels: 'Choose Predictive Models',
    timeSeries: 'Time Series Forecasting',
    timeSeriesDesc: 'Historical data trends to predict future market behavior',
    regression: 'Regression Analysis',
    regressionDesc: 'Statistical modeling to identify key drivers of market growth',
    scenarioAnalysis: 'Scenario Analysis',
    scenarioAnalysisDesc: 'Multiple scenarios (best/worst/likely) for strategic planning',

    defineCompetitiveFocus: 'Define Competitive Analysis Focus',
    marketShare: 'Market Share',
    pricingStrategy: 'Pricing Strategy',
    productDifferentiation: 'Product Differentiation',
    innovationCapacity: 'Innovation Capacity',
    customerBase: 'Customer Base',

    saveAsTemplate: 'Save as Template',
    generateReport: 'Generate Report',
    templateSaved: '配置已保存为模板'
  }
};
