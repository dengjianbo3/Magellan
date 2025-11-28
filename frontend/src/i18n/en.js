export default {
  // Common
  common: {
    save: 'Save',
    cancel: 'Cancel',
    delete: 'Delete',
    edit: 'Edit',
    view: 'View',
    download: 'Download',
    upload: 'Upload',
    share: 'Share',
    search: 'Search',
    filter: 'Filter',
    loading: 'Loading...',
    noData: 'No Data',
    confirm: 'Confirm',
    back: 'Back',
    next: 'Next',
    previous: 'Previous',
    finish: 'Finish',
    close: 'Close',
    settings: 'Settings',
    logout: 'Logout'
  },

  // Sidebar
  sidebar: {
    dashboard: 'Dashboard',
    reports: 'Reports',
    analysis: 'Analysis',
    roundtable: 'Roundtable',
    agents: 'AI Agents',
    knowledge: 'Knowledge Base',
    settings: 'Settings',
    collapse: 'Collapse',
    startNewAnalysis: 'Start New Analysis',
    brandSubtitle: 'AI INVESTMENT'
  },

  // Dashboard
  dashboard: {
    title: 'Dashboard Overview',
    welcome: "Welcome back! Here's what's happening with your investment analysis.",
    exportReport: 'Export Report',

    stats: {
      totalReports: 'Total Reports',
      activeAnalyses: 'Active Analyses',
      aiAgents: 'AI Agents',
      successRate: 'Success Rate'
    },

    analysisTrends: 'Analysis Trends',
    agentPerformance: 'Agent Performance',
    recentReports: 'Recent Reports',
    viewAll: 'View All',
    quickActions: 'Quick Actions',
    activeAgents: 'Active AI Agents',

    timeRanges: {
      last7Days: 'Last 7 days',
      last30Days: 'Last 30 days',
      last3Months: 'Last 3 months',
      thisMonth: 'This month',
      lastMonth: 'Last month',
      allTime: 'All time'
    },

    chartLabels: {
      reportsGenerated: 'Reports Generated',
      analysesStarted: 'Analyses Started'
    },

    quickActionItems: {
      newAnalysis: {
        title: 'New Analysis',
        description: 'Start a new project analysis'
      },
      uploadData: {
        title: 'Upload Data',
        description: 'Import data to knowledge base'
      },
      configureAgent: {
        title: 'Configure Agent',
        description: 'Set up a new AI agent'
      },
      viewReports: {
        title: 'View Reports',
        description: 'Browse all generated reports'
      }
    },

    agentStatus: {
      active: 'active',
      idle: 'idle',
      tasks: 'tasks'
    }
  },

  // Analysis Wizard
  analysis: {
    title: 'Start New Analysis',
    subtitle: 'Follow the steps below to configure your investment analysis project',

    steps: {
      projectInfo: {
        title: 'Project Info',
        description: 'Basic details'
      },
      selectAgents: {
        title: 'Select Agents',
        description: 'Choose AI agents'
      },
      configure: {
        title: 'Configure',
        description: 'Data & settings'
      }
    },

    step1: {
      title: 'Project Information',
      projectName: 'Project Name',
      projectNamePlaceholder: 'e.g., Tesla Q4 2024 Investment Analysis',
      company: 'Company/Target',
      companyPlaceholder: 'e.g., Tesla Inc.',
      analysisType: 'Analysis Type',
      description: 'Project Description',
      descriptionPlaceholder: 'Provide additional context about this analysis project...',
      required: 'Required',

      types: {
        dueDiligence: {
          name: 'Due Diligence',
          description: 'Comprehensive investment analysis'
        },
        marketAnalysis: {
          name: 'Market Analysis',
          description: 'Market trends and positioning'
        },
        financialReview: {
          name: 'Financial Review',
          description: 'Financial health assessment'
        },
        competitiveAnalysis: {
          name: 'Competitive Analysis',
          description: 'Competitor landscape review'
        }
      }
    },

    step2: {
      title: 'Select AI Agents',
      subtitle: 'Choose which AI agents should participate in this analysis',
      agentsParticipating: 'agents participating',

      agents: {
        marketAnalyst: {
          name: 'Market Analyst',
          role: 'Market Intelligence',
          description: 'Analyzes market trends, competition, and industry dynamics',
          speed: 'Fast',
          expertise: 'Market Research'
        },
        financialExpert: {
          name: 'Financial Expert',
          role: 'Financial Analysis',
          description: 'Reviews financial statements, ratios, and valuations',
          speed: 'Medium',
          expertise: 'Finance & Accounting'
        },
        teamEvaluator: {
          name: 'Team Evaluator',
          role: 'Team Assessment',
          description: 'Evaluates management team, culture, and organizational structure',
          speed: 'Medium',
          expertise: 'HR & Leadership'
        },
        riskAssessor: {
          name: 'Risk Assessor',
          role: 'Risk Management',
          description: 'Identifies and analyzes potential risks and challenges',
          speed: 'Fast',
          expertise: 'Risk Analysis'
        },
        techSpecialist: {
          name: 'Tech Specialist',
          role: 'Technology Review',
          description: 'Assesses technology stack, innovation, and technical capabilities',
          speed: 'Slow',
          expertise: 'Technology'
        },
        legalAdvisor: {
          name: 'Legal Advisor',
          role: 'Legal Compliance',
          description: 'Reviews legal structure, compliance, and regulatory issues',
          speed: 'Slow',
          expertise: 'Legal & Compliance'
        }
      }
    },

    step3: {
      title: 'Data Sources & Configuration',
      dataSources: 'Data Sources',
      uploadDocuments: 'Upload Additional Documents',
      uploadPrompt: 'Click to upload or drag and drop',
      uploadHint: 'PDF, DOCX, XLSX, CSV (Max 50MB)',
      analysisPriority: 'Analysis Priority',

      sources: {
        financialReports: {
          name: 'Financial Reports',
          description: 'Annual reports, 10-K, 10-Q filings',
          status: 'Available'
        },
        marketData: {
          name: 'Market Data',
          description: 'Stock prices, market cap, trading volume',
          status: 'Real-time'
        },
        newsSentiment: {
          name: 'News & Sentiment',
          description: 'News articles, social media sentiment',
          status: 'Available'
        },
        companyData: {
          name: 'Company Database',
          description: 'Company profiles, industry data',
          status: 'Available'
        }
      },

      priorities: {
        low: {
          name: 'Low Priority',
          time: '3-5 days'
        },
        normal: {
          name: 'Normal',
          time: '1-2 days'
        },
        high: {
          name: 'High Priority',
          time: '< 24 hours'
        }
      }
    },

    buttons: {
      previous: 'Previous',
      next: 'Next',
      cancel: 'Cancel',
      startAnalysis: 'Start Analysis'
    }
  },

  // Agent Chat
  agentChat: {
    activeAgents: 'Active Agents',
    agentsParticipating: 'agents participating',
    pauseAll: 'Pause All Agents',
    exportDiscussion: 'Export Discussion',

    status: {
      inProgress: 'In Progress',
      completed: 'Completed',
      paused: 'Paused'
    },

    started: 'Started',
    isThinking: 'is thinking...',

    sendMessage: 'Send',
    inputPlaceholder: 'Ask a question or provide additional context...',
    ctrlEnterHint: 'Press Ctrl+Enter to send',

    analysisProgress: 'Analysis Progress',
    overallProgress: 'Overall Progress',
    keyInsights: 'Key Insights',
    quickActions: 'Quick Actions',

    insights: {
      by: 'By'
    },

    actions: {
      viewRawData: 'View Raw Data',
      generateReport: 'Generate Report',
      shareAnalysis: 'Share Analysis'
    },

    tasks: {
      marketAnalysis: 'Market Analysis',
      financialReview: 'Financial Review',
      riskAssessment: 'Risk Assessment',
      teamEvaluation: 'Team Evaluation',
      techAssessment: 'Tech Assessment',
      finalReport: 'Final Report'
    },

    taskStatus: {
      completed: 'Completed',
      inProgress: 'In Progress',
      pending: 'Pending'
    },

    hitl: {
      requiredTitle: 'Preliminary Analysis Complete. Please Review.',
      keyQuestions: 'Key Due Diligence Questions',
      answerPlaceholder: 'Enter your answer or notes here...',
      actionRequired: 'Action Required: Select an Option'
    },

    report: {
      preliminaryMemo: 'Preliminary Investment Memo',
      companyInfo: 'Company Info',
      name: 'Name',
      industry: 'Industry',
      stage: 'Stage',
      teamAssessment: 'Team Assessment',
      teamAnalysisCompleted: 'Team analysis completed.',
      marketAnalysis: 'Market Analysis',
      marketAnalysisCompleted: 'Market analysis completed.',
      savedSuccess: 'Analysis Completed Successfully!',
      saveButton: 'Save Analysis Report',
      savedButton: 'Report Saved',
      viewFull: 'View Full Report'
    },

    sidebar: {
      elapsedTime: 'Elapsed Time',
      estRemaining: 'Est. Remaining',
      currentAction: 'Current Action',
      processing: 'Processing...',
      configuration: 'Configuration',
      company: 'Company',
      type: 'Type',
      agents: 'Agents',
      active: 'Active'
    }
  },

  // Scenarios (Mock Data Fallback)
  scenarios: {
    earlyStage: {
      name: 'Early Stage VC',
      description: 'Analyze pre-seed/seed startups focusing on team and market potential.'
    },
    growth: {
      name: 'Growth Equity',
      description: 'Evaluate scaling companies with established metrics and unit economics.'
    },
    publicMarket: {
      name: 'Public Markets',
      description: 'Comprehensive analysis of publicly traded securities and reports.'
    },
    industryResearch: {
      name: 'Industry Research',
      description: 'Deep dive into specific market sectors and competitive landscapes.'
    },
    alternative: {
      name: 'Alternative Assets',
      description: 'Real estate, crypto, and other non-traditional asset classes.'
    }
  },

  // Reports
  reports: {
    title: 'Reports',
    subtitle: 'Manage and view all generated analysis reports',
    newReport: 'New Report',

    filters: {
      allTypes: 'All Types',
      allStatus: 'All Status',
      dueDiligence: 'Due Diligence',
      marketAnalysis: 'Market Analysis',
      financialReview: 'Financial Review',
      completed: 'Completed',
      inProgress: 'In Progress',
      draft: 'Draft'
    },

    searchPlaceholder: 'Search reports...',

    card: {
      agents: 'agents',
      view: 'View',
      download: 'Download',
      share: 'Share'
    },

    status: {
      completed: 'Completed',
      inProgress: 'In Progress',
      draft: 'Draft'
    }
  },

  // AI Agents
  agents: {
    title: 'AI Agents',
    subtitle: 'Configure and manage your AI analysis agents',
    createCustomAgent: 'Create Custom Agent',

    card: {
      analyses: 'Analyses',
      avgResponse: 'Avg Response',
      capabilities: 'Capabilities',
      configure: 'Configure',
      pause: 'Pause',
      activate: 'Activate'
    },

    configModal: {
      title: 'Configure Agent',
      agentName: 'Agent Name',
      aiModel: 'AI Model',
      temperature: 'Temperature',
      temperatureHint: {
        precise: 'Precise',
        creative: 'Creative'
      },
      systemPrompt: 'System Prompt',
      maxTokens: 'Max Tokens',
      saveChanges: 'Save Changes',
      cancel: 'Cancel',

      models: {
        gpt4: 'GPT-4 (Most Accurate)',
        gpt35: 'GPT-3.5 (Balanced)',
        claude2: 'Claude 2 (Long Context)'
      }
    }
  },

  // Knowledge Base
  knowledge: {
    title: 'Knowledge Base',
    documentsCount: 'documents',
    searchPlaceholder: 'Search documents...',
    upload: 'Upload',
    newCategory: 'New Category',

    categories: {
      all: 'All Documents',
      financial: 'Financial Reports',
      market: 'Market Research',
      legal: 'Legal Documents',
      other: 'Other'
    },

    table: {
      name: 'Name',
      type: 'Type',
      size: 'Size',
      uploaded: 'Uploaded',
      status: 'Status',
      actions: 'Actions'
    },

    status: {
      processed: 'Processed',
      processing: 'Processing',
      failed: 'Failed'
    },

    empty: {
      title: 'No documents found',
      subtitle: 'Upload documents to get started',
      uploadButton: 'Upload Document'
    },

    uploadModal: {
      title: 'Upload Documents',
      category: 'Category',
      files: 'Files',
      uploadPrompt: 'Click to upload or drag and drop',
      uploadHint: 'PDF, DOCX, XLSX, CSV, TXT (Max 100MB)',
      upload: 'Upload',
      file: 'file',
      files: 'files',
      cancel: 'Cancel'
    }
  },

  // Settings
  settings: {
    title: 'Settings',
    subtitle: 'Manage your account and application preferences',

    sections: {
      profile: 'Profile',
      notifications: 'Notifications',
      security: 'Security',
      api: 'API Keys',
      appearance: 'Appearance'
    },

    profile: {
      title: 'Profile Settings',
      changeAvatar: 'Change Avatar',
      firstName: 'First Name',
      lastName: 'Last Name',
      email: 'Email',
      role: 'Role',
      saveChanges: 'Save Changes'
    },

    notifications: {
      title: 'Notification Preferences',
      analysisComplete: {
        title: 'Analysis Complete',
        description: 'Get notified when analysis is finished'
      },
      agentUpdates: {
        title: 'Agent Updates',
        description: 'Notifications for agent status changes'
      },
      weeklyReports: {
        title: 'Weekly Reports',
        description: 'Receive weekly activity summary'
      },
      emailNotifications: {
        title: 'Email Notifications',
        description: 'Send notifications to email'
      }
    },

    security: {
      title: 'Security Settings',
      changePassword: 'Change Password',
      currentPassword: 'Current Password',
      newPassword: 'New Password',
      confirmPassword: 'Confirm New Password',
      updatePassword: 'Update Password',
      twoFactorAuth: 'Two-Factor Authentication',
      enable2FA: {
        title: 'Enable 2FA',
        description: 'Add an extra layer of security',
        button: 'Enable'
      }
    },

    api: {
      title: 'AI Model Configuration',
      llmProvider: 'LLM Provider',
      llmProviderDesc: 'Select the LLM provider for AI analysis',
      providers: {
        gemini: 'Gemini (Google)',
        kimi: 'Kimi (Moonshot AI)'
      },
      currentModel: 'Current Model',
      providerStatus: 'Status',
      available: 'Available',
      unavailable: 'Not Configured',
      switching: 'Switching...',
      switchSuccess: 'Switched to {provider}',
      switchError: 'Switch failed: {error}',
      update: 'Update',
      usage: 'API Usage',
      thisMonth: 'This Month'
    },

    appearance: {
      title: 'Appearance',
      theme: 'Theme',
      themes: {
        light: 'Light',
        dark: 'Dark',
        auto: 'Auto'
      },
      language: 'Language',
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
    selectScenario: 'Select Investment Scenario',
    selectScenarioHint: 'Please select the scenario type that best matches your investment needs',
    loadingScenarios: 'Loading scenarios...',
    selected: 'Selected',
    comingSoon: 'Coming Soon',
    recommended: 'Recommended',
    na: 'N/A',
    quickJudgment: 'Quick Judgment',
    standardAnalysis: 'Standard Analysis',
    nextStep: 'Next',

    // Analysis Config
    configAnalysis: 'Configure Analysis',
    configAnalysisHint: 'Select analysis depth and focus areas',
    configureIndustryAnalysis: 'Configure Industry Analysis',
    configureIndustryAnalysisHint: 'Define the parameters for your AI-driven research report',
    analysisDepth: 'Analysis Depth',
    quickMode: 'Quick Mode',
    standardMode: 'Standard Mode',
    comprehensiveMode: 'Comprehensive Mode',
    timeframe: 'Timeframe',
    focusAreas: 'Focus Areas',
    optional: 'Optional',
    reportLanguage: 'Report Language',
    analysisSummary: 'Analysis Summary',
    depth: 'Depth',
    estimatedTime: 'Estimated Time',
    startAnalysis: 'Start Analysis',

    // Config sections
    defineResearchScope: 'Define Your Research Scope',
    selectResearchMethodologies: 'Select Research Methodologies',
    setDataSourcePreferences: 'Set Data Source Preferences',
    choosePredictiveModels: 'Choose Predictive Models',
    defineCompetitiveAnalysisFocus: 'Define Competitive Analysis Focus',

    // Form fields
    industryTopic: 'Industry/Topic',
    industryTopicLabel: 'Industry/Topic to Analyze',
    industryTopicPlaceholder: 'e.g., "Global Electric Vehicle Market"',
    geography: 'Geography',
    geographyPlaceholder: 'Please select a geographic area',
    geographyGlobal: 'Global',
    geographyNorthAmerica: 'North America',
    geographyEurope: 'Europe',
    geographyAsiaPacific: 'Asia Pacific',
    geographyChina: 'China',
    mainProducts: 'Main Products/Services',
    mainProductsPlaceholder: 'e.g., GPU, TPU, AI accelerators',
    marketSize: 'Market Size (in billions)',
    marketSizePlaceholder: 'e.g., 50',
    maxSize: 'Max Size',
    maxSizePlaceholder: 'e.g., 200',
    keyCompetitors: 'Key Competitors',
    keyCompetitorsPlaceholder: 'e.g., Google (Enter to add multiple competitors)',

    // Methodologies
    swotAnalysis: 'SWOT Analysis',
    portersFiveForces: "Porter's Five Forces",
    pestleAnalysis: 'PESTLE Analysis',
    valueChainAnalysis: 'Value Chain Analysis',

    // Hints
    selectDataSources: 'Select the data sources to include in your analysis',
    selectPredictiveModels: 'Select the AI models to use for predictions',
    specifyCompetitiveParams: 'Specify the competitive analysis parameters',

    // Actions
    saveAsTemplate: 'Save as Template',
    generateReport: 'Generate Report',

    // Early Stage Input
    earlyStageInvestment: 'Early Stage Investment',
    earlyStageHint: 'Please provide basic information about the project',
    companyName: 'Company Name',
    companyNamePlaceholder: 'Enter company name',
    fundingStage: 'Funding Stage',
    selectStage: 'Select funding stage',
    industry: 'Industry',
    industryPlaceholder: 'e.g., Artificial Intelligence, Enterprise Services',
    businessPlan: 'Business Plan',
    uploadFile: 'Upload File',
    changeFile: 'Change File',
    uploading: 'Uploading',
    uploadFailed: 'Upload Failed',
    bpHint: 'Supports PDF, PPT, Word formats',
    foundedYear: 'Founded Year',
    foundedYearPlaceholder: 'Enter founded year',
    teamMembers: 'Team Members',
    teamMembersPlaceholder: 'One member per line, format: Name, Position, Background\nExample:\nJohn Doe, CEO, Former Google VP\nJane Smith, CTO, MIT PhD',
    teamMembersHint: 'Briefly describe core team members background',

    // Analysis Progress
    analyzing: 'Analyzing',
    analysisFor: 'Analysis for',
    analyzingHint: 'Analyzing... The system is currently processing real-time market data.',
    cancelAnalysis: 'Cancel Analysis',
    overallProgress: 'Overall Progress',
    estimatedTimeRemaining: 'Estimated Time Remaining',
    agentsActive: 'Agents Active',
    analysisStarted: 'Analysis Started',
    aiAgentStatus: 'AI Agent Status',
    analysisTimeline: 'Analysis Timeline',
    elapsedTime: 'Elapsed Time',
    completed: 'Completed',
    completedStatus: 'Completed',
    running: 'Running',
    runningStatus: 'Running',
    queued: 'Queued',
    inProgress: 'In Progress',
    pending: 'Pending',

    // Agent messages
    dataCollectionAgent: 'Data Collection Agent',
    completedFetched: 'Completed: Fetched real-time market data.',
    financialModelingAgent: 'Financial Modeling Agent',
    runningAnalyzing: 'Running: Analyzing financial statements...',
    valuationAgent: 'Valuation Agent',
    runningGenerating: 'Running: Generating valuation models...',
    riskAssessmentAgent: 'Risk Assessment Agent',
    queuedStatus: 'Queued',

    // Timeline events
    fetchingMarketData: 'Fetching Market Data',
    analyzingFinancialStatements: 'Analyzing Financial Statements',
    generatingValuationModels: 'Generating Valuation Models',
    finalReportCompilation: 'Final Report Compilation',

    quickJudgmentResult: 'Quick Judgment Result',
    recommendation: 'Recommendation',
    overallScore: 'Overall Score',
    scores: 'Scores',
    verdict: 'Verdict',
    advantages: 'Advantages',
    concerns: 'Concerns',
    nextSteps: 'Next Steps',
    upgradeToStandard: 'Upgrade to Standard Analysis',
    exportReport: 'Export Report',
    viewFullReport: 'View Full Report',
    analysisCompleted: 'Analysis Completed',
    analysisCompletedHint: 'You can view the complete analysis report',

    // Progress Steps
    workflowStarted: 'Workflow Started',
    stepInProgress: 'In Progress',
    stepCompleted: 'Completed',
    connectingWebSocket: 'Connecting to real-time channel...',
    waitingForResults: 'Waiting for analysis results...',

    // Wizard Steps
    inputTarget: 'Input Target',

    // Step Result Card
    tam: 'TAM',
    sam: 'SAM',
    growthRate: 'Growth Rate',
    marketMaturity: 'Market Maturity',
    score: '',
    topPlayers: 'Top Players',
    marketConcentration: 'Market Concentration',
    entryBarriers: 'Entry Barriers',
    keyTrends: 'Key Trends',
    techDirection: 'Tech Direction',
    policySupport: 'Policy Support',
    investmentOpportunities: 'Investment Opportunities',
    subSectors: 'Sub-sectors',
    revenueAssessment: 'Revenue Assessment',
    cashFlow: 'Cash Flow',
    profitability: 'Profitability',
    concernsLabel: 'Concerns',
    valuationLevel: 'Valuation Level',
    peRatio: 'PE Ratio',
    priceTarget: 'Price Target',

    // Time units
    minutes: 'm',
    seconds: 's',
    minute: 'min',
    second: 'sec',

    // Recommendations
    recommendationBuy: 'Buy',
    recommendationPass: 'Pass',
    recommendationFurtherDD: 'Further Due Diligence',
    recommendationInvest: 'Invest',

    // Alerts
    upgradeFeatureInDevelopment: 'Upgrade to standard analysis feature is under development...',
    exportFeatureInDevelopment: 'Export report feature is under development...',
  },

  // Roundtable Discussion
  roundtable: {
    title: 'Roundtable Discussion',
    subtitle: 'Multiple investment experts discuss and analyze topics from different perspectives',

    startPanel: {
      title: 'Start New Roundtable Discussion',
      topicLabel: 'Discussion Topic',
      topicPlaceholder: 'e.g., Tesla Q4 2024 Investment Value Analysis',
      expertsLabel: 'Participating Experts',
      expertsSelected: 'selected',
      roundsLabel: 'Discussion Rounds',
      rounds: 'rounds',
      startButton: 'Start Discussion',
      required: 'Required'
    },

    experts: {
      leader: {
        name: 'Leader',
        role: 'Discussion Host',
        description: 'Host discussion, synthesize viewpoints, and form final conclusions'
      },
      marketAnalyst: {
        name: 'Market Analyst',
        role: 'Market Research',
        description: 'Analyze market trends, competition, and industry dynamics'
      },
      financialExpert: {
        name: 'Financial Expert',
        role: 'Financial Analysis',
        description: 'Review financial statements, valuations, and financial health'
      },
      teamEvaluator: {
        name: 'Team Evaluator',
        role: 'Team Assessment',
        description: 'Evaluate management team, organizational culture, and execution capabilities'
      },
      riskAssessor: {
        name: 'Risk Assessor',
        role: 'Risk Management',
        description: 'Identify and analyze potential risks and challenges'
      }
    },

    discussion: {
      progress: 'Discussion Progress',
      currentRound: 'Current Round',
      messageCount: 'Message Count',
      participants: 'Participating Experts',
      stopButton: 'Stop Discussion',
      exportButton: 'Export Results',
      status: {
        running: 'In Progress',
        completed: 'Completed'
      },
      startedAt: 'Started at',
      connecting: 'Connecting to roundtable discussion...'
    },

    summary: {
      title: 'Discussion Summary',
      completed: 'Roundtable discussion completed'
    },

    // Human-in-the-Loop (HITL)
    hitl: {
      interruptButton: 'Interrupt & Add Input',
      dialogTitle: 'Interrupt and Provide Feedback',
      respondingTo: 'You are responding to:',
      inputLabel: 'Your Input',
      inputPlaceholder: 'Enter your feedback, such as:\n- Correct expert analysis errors\n- Provide additional context\n- Raise new concerns\n- Share internal data\n\nThe Leader will re-plan the discussion based on your input.',
      inputHint: 'Tip: Your input will be shared with all experts. The Leader will adjust the discussion accordingly.',
      submit: 'Send Input',
      submitting: 'Sending...',
      cancel: 'Cancel',
      interventionSent: 'Your input has been sent. The Leader will re-plan the discussion.',
      interventionError: 'Failed to send input'
    }
  },

  // Early Stage Investment
  earlyStage: {
    // Progress Steps
    selectScenario: 'Select Investment Scenario',
    inputTarget: 'Input Target',
    configAnalysis: 'Configure Analysis',
    analyzing: 'Analyzing',

    // Input Target
    title: 'Early Stage Investment Analysis',
    subtitle: 'Analyze Angel, Seed, Pre-A, and Series A companies focusing on team, market opportunity, and innovation',
    companyName: 'Company Name',
    companyNamePlaceholder: 'e.g., Tech Startup Inc.',
    companyNameHint: 'Enter the company name to analyze',
    fundingStage: 'Funding Stage',
    selectStage: 'Please select funding stage',
    industry: 'Industry',
    industryPlaceholder: 'e.g., AI, Electric Vehicles',
    businessPlan: 'Business Plan (Optional)',
    clickToUpload: 'Click to upload file',
    supportedFormats: 'Supports PDF, PPT, Word formats',
    uploadError: 'File upload failed',
    foundedYear: 'Founded Year',
    foundedYearPlaceholder: 'e.g., 2023',
    teamMembers: 'Team Members',
    teamMembersPlaceholder: 'One member per line, format: Name, Role, Background\nExample:\nJohn Doe, CEO, Former Google Tech Lead\nJane Smith, CTO, Stanford PhD',
    teamMembersHint: 'Enter team member information, one per line, comma-separated',
    uploading: 'Uploading',
    back: 'Back',
    next: 'Next',

    // Config Analysis
    configTitle: 'Configure New Early-Stage Analysis',
    configSubtitle: 'Define the parameters below to generate your investment report',
    projectName: 'Project/Analysis Name',
    projectNamePlaceholder: 'Enter the project or company name',
    selectDataSources: 'Select Data Sources',
    publicMarketData: 'Public Market Data',
    paidIndustryReports: 'Paid Industry Reports',
    internalKnowledge: 'Internal Knowledge Base',
    newsSocial: 'News & Social Feeds',
    definePriorities: 'Define Analysis Priorities',
    teamFounder: 'Team & Founder Background',
    technologyProduct: 'Technology & IP Viability',
    marketSizeTAM: 'Market Size & TAM/SOM',
    competitiveLandscape: 'Competitive Landscape',
    setRiskAppetite: 'Set Risk Appetite',
    aggressive: 'Aggressive',
    aggressiveDesc: 'High Risk / Reward',
    balanced: 'Balanced',
    balancedDesc: 'Moderate Growth',
    conservative: 'Conservative',
    conservativeDesc: 'Steady Growth',
    reset: 'Reset',
    generateReport: 'Generate Report',

    // Agents
    teamEvaluationAgent: 'Team Evaluation Agent',
    analyzingTeamBackground: 'Analyzing team background...',
    marketAnalysisAgent: 'Market Analysis Agent',
    analyzingMarketSize: 'Analyzing market size...',
    riskAssessmentAgent: 'Risk Assessment Agent',
    scanningRedFlags: 'Scanning for red flags...'
  },

  // Growth Stage Investment
  growthStage: {
    // Input Target
    title: 'Growth Stage Investment Analysis',
    subtitle: 'Analyze Series B to Pre-IPO companies, focusing on financial health, growth potential, and market position',
    basicInfo: 'Basic Company Information',
    companyName: 'Company Name',
    companyNamePlaceholder: 'e.g., Acme Technologies',
    tickerSymbol: 'Ticker Symbol (Optional)',
    tickerSymbolPlaceholder: 'e.g., AAPL',
    industrySector: 'Industry/Sector (Optional)',
    industrySectorPlaceholder: 'e.g., Enterprise Software',
    headquarters: 'Headquarters Location (Optional)',
    headquartersPlaceholder: 'e.g., San Francisco',
    fundingStage: 'Funding Stage',
    seriesB: 'Series B',
    seriesC: 'Series C',
    seriesD: 'Series D',
    seriesE: 'Series E',
    preIPO: 'Pre-IPO',
    financialData: 'Financial Data',
    financialDataHint: 'Upload financial statements, annual reports, or audit reports to help us accurately assess the company\'s financial health',
    clickToUpload: 'Click to upload file',
    dragAndDrop: 'or drag and drop file here',
    supportedFormats: 'Supports CSV, XLSX, PDF formats',
    marketPositioning: 'Market Positioning & Strategy',
    coreProducts: 'Core Products/Services',
    coreProductsPlaceholder: 'Please briefly describe the company\'s core products or services...',
    competitiveLandscape: 'Competitive Landscape',
    competitorName: 'Competitor Name',
    marketShare: 'Market Share (%)',
    addCompetitor: 'Add Competitor',

    // Config Analysis
    configTitle: 'Configure Growth Stage Investment Analysis',
    configSubtitle: 'Set up the detailed parameters for your long-term investment analysis',
    growthModelSelection: 'Growth Model Selection',
    sCurveGrowth: 'S-Curve Growth',
    sCurveGrowthDesc: 'Models growth that is initially exponential, then slows as saturation is reached',
    linearGrowth: 'Linear Growth',
    linearGrowthDesc: 'Models steady, constant rate of growth over time',
    exponentialGrowth: 'Exponential Growth',
    exponentialGrowthDesc: 'Models accelerating growth where the rate itself increases over time',
    pleaseSelectGrowthModel: 'Please select a growth model',

    competitionAnalysisFocus: 'Competition Analysis Focus',
    competitiveAdvantages: 'Competitive Advantages',
    technologyLeadership: 'Technology Leadership',
    brandRecognition: 'Brand Recognition',
    networkEffects: 'Network Effects',
    costAdvantage: 'Cost Advantage',
    dataAdvantage: 'Data Advantage',
    competitionIntensity: 'Competition Intensity',
    lowCompetition: 'Low Competition',
    mediumCompetition: 'Medium Competition',
    highCompetition: 'High Competition',

    marketOutlookAssessment: 'Market Outlook Assessment',
    marketGrowthRate: 'Market Growth Rate',
    marketGrowthRateHint: 'Expected annual market growth rate (CAGR)',
    marketMaturity: 'Market Maturity',
    emergingMarket: 'Emerging Market',
    growingMarket: 'Growing Market',
    matureMarket: 'Mature Market',
    keyMarketDrivers: 'Key Market Drivers',
    keyMarketDriversPlaceholder: 'Describe the key factors driving market growth...',

    financialProjections: 'Financial Projections',
    projectionPeriod: 'Projection Period',
    threeYears: '3 Years',
    fiveYears: '5 Years',
    tenYears: '10 Years',
    revenueGrowthAssumption: 'Revenue Growth Assumption',
    profitMarginTarget: 'Profit Margin Target',
    burnRateAssumption: 'Burn Rate Assumption',
    monthlyBurnRate: 'Monthly Burn Rate',
    keyFinancialMetrics: 'Key Financial Metrics',
    revenue: 'Revenue',
    grossMargin: 'Gross Margin',
    operatingMargin: 'Operating Margin',
    netIncome: 'Net Income',
    cashFlow: 'Cash Flow',
    cac: 'Customer Acquisition Cost (CAC)',
    ltv: 'Lifetime Value (LTV)',
    runway: 'Runway',

    // Agents
    financialHealthAgent: 'Financial Health Agent',
    analyzingFinancialHealth: 'Analyzing financial health...',
    growthPotentialAgent: 'Growth Potential Agent',
    assessingGrowthPotential: 'Assessing growth potential...',
    marketPositionAgent: 'Market Position Agent',
    analyzingMarketPosition: 'Analyzing market position...'
  },

  // Public Market Investment
  publicMarket: {
    // Input Target
    title: 'Public Market Investment Analysis',
    subtitle: 'Analyze listed stocks, ETFs, or indices focusing on valuation, fundamentals, technicals, and sentiment',
    targetCompany: 'Target Company',
    tickerOrName: 'Enter Company Ticker or Name',
    searchPlaceholder: 'Search for AAPL or Apple Inc.',
    tickerHint: 'Enter ticker symbol (e.g., AAPL) or company name to search',
    tickerRequired: 'Please enter a ticker symbol',

    selectResearchPeriod: 'Select Research Period',
    quarterly: 'Quarterly',
    annually: 'Annually',
    customRange: 'Custom Range',
    startDate: 'Start Date',
    endDate: 'End Date',
    customRangeRequired: 'Please select custom date range',

    chooseKeyMetrics: 'Choose Key Metrics',
    peRatio: 'PE Ratio',
    priceToSales: 'Price-to-Sales',
    roe: 'ROE',
    debtToEquity: 'Debt-to-Equity',
    ebitdaMargin: 'EBITDA Margin',
    addMetric: 'Add Metric',
    enterCustomMetric: 'Please enter custom metric name',

    uploadFilings: 'Upload Filings or Research',
    clickToUpload: 'Click to upload or drag and drop',
    uploadHint: 'SEC filings, research reports or other relevant documents',

    // Config Analysis
    allocationAnalysis: 'Allocation Analysis',
    configureParameters: 'Configure parameters for your public market investment analysis',
    generateReport: 'Generate Report',

    configureDataSources: 'Configure Data Sources',
    realTimeQuotes: 'Real-time Quotes',
    financialFilings: 'Financial Filings',
    timePeriod: 'Time Period',
    newsSocialMedia: 'News & Social Media',
    selectAtLeastOneDataSource: 'Please select at least one data source',

    defineAgentFocus: 'Define AI Agent Focus',
    weight: 'Weight',
    sentimentAnalysis: 'Sentiment Analysis',
    quantitativeStrategy: 'Quantitative Strategy',
    fundamentalAnalysis: 'Fundamental Analysis',
    technicalIndicators: 'Technical Indicators',

    setRiskParameters: 'Set Risk Parameters',
    riskAppetite: 'Risk Appetite',
    conservative: 'Conservative',
    moderate: 'Moderate',
    aggressive: 'Aggressive',
    maxDrawdown: 'Max Drawdown (%)',
    targetReturn: 'Target Return (%)',
    timeHorizon: 'Time Horizon',
    shortTerm: 'Short Term',
    mediumTerm: 'Medium Term',
    longTerm: 'Long Term'
  },

  // Alternative Investment
  alternative: {
    title: 'Alternative Investment Analysis',
    subtitle: 'Analyze crypto, DeFi, NFT and other alternative investments, focusing on tech foundation, tokenomics, and community activity',

    // Input form
    projectOverview: 'Project Overview',
    projectOverviewDesc: 'Provide basic information about the project',
    assetClass: 'Asset Class',
    selectAssetClass: 'Select Asset Class',
    crypto: 'Cryptocurrency',
    defi: 'DeFi - Decentralized Finance',
    nft: 'NFT - Digital Collectibles',
    web3: 'Web3 Applications',
    projectName: 'Project Name',
    projectNamePlaceholder: 'e.g., Bitcoin, Uniswap, Bored Ape...',
    investmentSize: 'Investment Size',
    investmentSizePlaceholder: 'Enter investment amount',

    documentation: 'Due Diligence Documentation',
    documentationDesc: 'Upload whitepaper, audit reports, and other materials',
    uploadDocs: 'Upload Documents',
    uploadHint: 'Click or drag files here to upload',
    supportedFormats: 'Supports PDF, DOC, DOCX, TXT formats',

    keyStakeholders: 'Key Stakeholders',
    stakeholdersDesc: 'Core team member information',
    name: 'Name',
    namePlaceholder: 'Member name',
    role: 'Role',
    rolePlaceholder: 'Position/Role',
    addMember: 'Add Member',
    removeMember: 'Remove Member',

    analysisDirectives: 'Analysis Directives',
    directivesDesc: 'Key questions or areas of focus for analysis',
    directivesPlaceholder: 'For example:\n- Assess technical innovation\n- Analyze token economics sustainability\n- Community governance effectiveness\n- Competitive landscape and positioning',

    riskWarning: 'Investment Risk Warning',
    riskWarningText: 'Alternative investments carry high risk. Please evaluate carefully. Only invest what you can afford to lose.',

    // Config form
    allocationAnalysis: 'Allocation Analysis',
    configSubtitle: 'Configure the parameters for your alternative investment analysis report',

    valuationModel: 'Valuation Model',
    dcf: 'DCF - Discounted Cash Flow',
    dcfTitle: 'Discounted Cash Flow Model',
    dcfDesc: 'Values the project by forecasting future cash flows and discounting to present value. Suitable for DeFi protocols or NFT platforms with stable revenue expectations.',
    comparableCompany: 'Comparable Company Analysis',
    comparableTitle: 'Comparable Company Analysis',
    comparableDesc: 'Values the target by comparing metrics (e.g., TVL/Market Cap ratio, user count) with similar projects. Suitable for mature sectors with multiple competitors.',
    precedentTransactions: 'Precedent Transactions',
    precedentTitle: 'Precedent Transactions Method',
    precedentDesc: 'Values based on historical funding or acquisition prices of similar projects. Suitable for sectors with sufficient M&A examples.',
    moreInfo: 'More Information',

    dueDiligenceFocus: 'Due Diligence Focus',
    legalCompliance: 'Legal & Compliance',
    operationalRisk: 'Operational Risk',
    financialIntegrity: 'Financial Statements Integrity',
    marketCompetition: 'Market Competition',

    exitStrategyPreference: 'Exit Strategy Preference',
    ipo: 'IPO',
    strategicAcquisition: 'Strategic Acquisition (M&A)',
    ipoPreferred: 'IPO exit preferred',
    acquisitionPreferred: 'M&A exit preferred',
    balancedExit: 'Balanced multiple exit strategies',

    analysisDepth: 'Analysis Depth',
    quickAnalysis: 'Quick Analysis',
    standardAnalysis: 'Standard Analysis',
    deepAnalysis: 'Deep Analysis',

    riskTolerance: 'Risk Tolerance',
    conservative: 'Conservative',
    moderate: 'Moderate',
    aggressive: 'Aggressive',

    resetToDefault: 'Reset to Default',
    generateReport: 'Generate Report',

    // Agents
    techFoundationAgent: 'Tech Foundation Agent',
    analyzingTechFoundation: 'Analyzing technical architecture and security...',
    tokenomicsAgent: 'Tokenomics Agent',
    analyzingTokenomics: 'Analyzing token model and economic mechanisms...',
    communityAgent: 'Community Activity Agent',
    analyzingCommunity: 'Analyzing community engagement and governance...',

    // Validation
    assetClassRequired: 'Please select an asset class',
    projectNameRequired: 'Please enter project name',
    investmentSizeRequired: 'Please enter investment size',
    investmentSizePositive: 'Investment size must be greater than 0'
  },

  // Industry Research
  industryResearch: {
    title: 'Industry Research Analysis',
    subtitle: 'Systematic analysis of industry trends, competitive landscape, investment opportunities, and risk factors',

    // Input page
    defineTarget: 'Define Your Research Target',
    defineTargetDesc: 'Provide basic information about the industry or market you want to analyze',
    industryName: 'Industry Name',
    industryPlaceholder: 'e.g., AI Chipsets',
    researchScope: 'Research Scope',
    selectScope: 'Please select one or more regions',
    global: 'Global',
    china: 'China',
    us: 'United States',
    europe: 'Europe',
    asia: 'Asia-Pacific',
    mainProducts: 'Main Products/Services',
    mainProductsPlaceholder: 'e.g., GPU, TPU, AI Accelerators',
    marketSize: 'Market Size (Billion Yuan)',
    marketSizePlaceholder: 'e.g., 50',
    billionYuan: 'Billion Yuan',
    maxRegions: 'Max Scale',
    maxRegionsPlaceholder: 'e.g., 200',
    keyParticipants: 'Key Participants',
    participantPlaceholder: 'e.g., Google (press Enter to add)',
    participantHint: 'Type company name and press Enter to add tag',
    startAnalysis: 'Start Analysis',
    industryNameRequired: 'Please enter industry name',
    marketResearch: ' Market Research',

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
    templateSaved: 'Configuration saved as template'
  }
};
