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
    startNewAnalysis: 'Start New Analysis'
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
      title: 'API Configuration',
      openaiKey: 'OpenAI API Key',
      claudeKey: 'Claude API Key',
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
    }
  }
};
