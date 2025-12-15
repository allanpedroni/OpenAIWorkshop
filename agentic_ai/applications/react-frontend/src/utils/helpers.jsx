import {
  Send as SendIcon,
  Assignment as PlanIcon,
  EmojiObjects as IdeaIcon,
  TrendingUp as ProgressIcon,
  CheckCircleOutline as ResultIcon,
} from '@mui/icons-material';

/**
 * Get display properties for orchestrator event types
 * @param {string} kind - The event kind
 * @returns {object} Display configuration with icon, label, color, and background color
 */
export const getOrchestratorDisplay = (kind) => {
  const displays = {
    instruction: {
      icon: <SendIcon fontSize="small" />,
      label: '📤 Instructing Agent',
      color: 'secondary',
      bgColor: '#f3e5f5',
    },
    task_ledger: {
      icon: <PlanIcon fontSize="small" />,
      label: '📋 Planning',
      color: 'info',
      bgColor: '#e3f2fd',
    },
    user_task: {
      icon: <IdeaIcon fontSize="small" />,
      label: '📝 Task Received',
      color: 'default',
      bgColor: '#f5f5f5',
    },
    notice: {
      icon: <ResultIcon fontSize="small" />,
      label: '📢 Notice',
      color: 'warning',
      bgColor: '#fff3e0',
    },
    // Legacy kinds from old implementation
    plan: {
      icon: <PlanIcon fontSize="small" />,
      label: '📋 Planning',
      color: 'primary',
      bgColor: '#e3f2fd',
    },
    progress: {
      icon: <ProgressIcon fontSize="small" />,
      label: '⚙️ Working',
      color: 'info',
      bgColor: '#e1f5fe',
    },
    result: {
      icon: <ResultIcon fontSize="small" />,
      label: '✅ Decision',
      color: 'success',
      bgColor: '#e8f5e9',
    },
  };

  return displays[kind] || {
    icon: <IdeaIcon fontSize="small" />,
    label: '💭 Thinking',
    color: 'default',
    bgColor: '#f5f5f5',
  };
};

/**
 * Get emoji representation for agent based on agent ID
 * @param {string} agentId - The agent identifier
 * @returns {string} Emoji representing the agent
 */
export const getAgentEmoji = (agentId) => {
  if (agentId.includes('crm') || agentId.includes('billing')) return '💳';
  if (agentId.includes('product') || agentId.includes('promotion')) return '🎁';
  if (agentId.includes('security') || agentId.includes('auth')) return '🔒';
  return '🤖';
};

/**
 * Build authorization headers for API requests
 * @param {string} accessToken - The access token (optional)
 * @returns {object} Headers object
 */
export const buildAuthHeaders = (accessToken) => {
  return accessToken ? { Authorization: `Bearer ${accessToken}` } : {};
};

/**
 * Scroll to a ref element smoothly
 * @param {React.RefObject} ref - The ref to scroll to
 */
export const scrollToRef = (ref) => {
  ref.current?.scrollIntoView({ behavior: 'smooth' });
};
