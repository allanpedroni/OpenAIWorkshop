import { useMemo, useEffect, useState, useCallback } from 'react';
import ReactFlow, {
  Background,
  Controls,
  MiniMap,
  useNodesState,
  useEdgesState,
} from 'reactflow';
import 'reactflow/dist/style.css';
import { Box, Popover, Paper, Typography, Chip, Divider, List, ListItem, ListItemIcon, ListItemText } from '@mui/material';
import FunctionsIcon from '@mui/icons-material/Functions';
import OutputIcon from '@mui/icons-material/Output';
import AccessTimeIcon from '@mui/icons-material/AccessTime';
import CheckCircleIcon from '@mui/icons-material/CheckCircle';
import HourglassEmptyIcon from '@mui/icons-material/HourglassEmpty';
import CustomNode from './CustomNode';
import { EXECUTOR_STATES } from '../constants/workflow';
import { getNodeStatusColor, getStatusLabel } from '../utils/uiHelpers';

const nodeTypes = {
  custom: CustomNode,
};

// Define the workflow graph structure
const initialNodes = [
  {
    id: 'alert_router',
    type: 'custom',
    position: { x: 400, y: 50 },
    data: { label: 'Alert Router', status: 'idle', description: 'Routes alerts to analysts' },
  },
  {
    id: 'usage_pattern_executor',
    type: 'custom',
    position: { x: 150, y: 200 },
    data: { label: 'Usage Analyst', status: 'idle', description: 'Analyzes usage patterns' },
  },
  {
    id: 'location_analysis_executor',
    type: 'custom',
    position: { x: 400, y: 200 },
    data: { label: 'Location Analyst', status: 'idle', description: 'Analyzes location anomalies' },
  },
  {
    id: 'billing_charge_executor',
    type: 'custom',
    position: { x: 650, y: 200 },
    data: { label: 'Billing Analyst', status: 'idle', description: 'Analyzes billing patterns' },
  },
  {
    id: 'fraud_risk_aggregator',
    type: 'custom',
    position: { x: 400, y: 350 },
    data: { label: 'Risk Aggregator', status: 'idle', description: 'Aggregates risk assessment' },
  },
  {
    id: 'review_gateway',
    type: 'custom',
    position: { x: 550, y: 500 },
    data: { label: 'Review Gateway', status: 'idle', description: 'Human analyst review (pauses workflow)' },
  },
  {
    id: 'auto_clear_executor',
    type: 'custom',
    position: { x: 250, y: 500 },
    data: { label: 'Auto Clear', status: 'idle', description: 'Auto-clears low risk' },
  },
  {
    id: 'fraud_action_executor',
    type: 'custom',
    position: { x: 550, y: 650 },
    data: { label: 'Fraud Action', status: 'idle', description: 'Execute fraud action' },
  },
  {
    id: 'final_notification_executor',
    type: 'custom',
    position: { x: 400, y: 800 },
    data: { label: 'Final Notification', status: 'idle', description: 'Send notifications' },
  },
];

const initialEdges = [
  // Fan-out from alert router to analysts
  { id: 'e1-1', source: 'alert_router', target: 'usage_pattern_executor', animated: true },
  { id: 'e1-2', source: 'alert_router', target: 'location_analysis_executor', animated: true },
  { id: 'e1-3', source: 'alert_router', target: 'billing_charge_executor', animated: true },
  
  // Fan-in to aggregator
  { id: 'e2-1', source: 'usage_pattern_executor', target: 'fraud_risk_aggregator' },
  { id: 'e2-2', source: 'location_analysis_executor', target: 'fraud_risk_aggregator' },
  { id: 'e2-3', source: 'billing_charge_executor', target: 'fraud_risk_aggregator' },
  
  // Switch case from aggregator
  { id: 'e3-1', source: 'fraud_risk_aggregator', target: 'review_gateway', label: 'High Risk', style: { stroke: '#f44336' } },
  { id: 'e3-2', source: 'fraud_risk_aggregator', target: 'auto_clear_executor', label: 'Low Risk', style: { stroke: '#4caf50' } },
  
  // Review gateway to fraud action (human review happens via request_info, then proceeds)
  { id: 'e4-1', source: 'review_gateway', target: 'fraud_action_executor', animated: true, style: { stroke: '#ff9800' } },
  
  // Final paths
  { id: 'e5-1', source: 'auto_clear_executor', target: 'final_notification_executor' },
  { id: 'e5-2', source: 'fraud_action_executor', target: 'final_notification_executor' },
];

/**
 * Workflow visualizer component using React Flow
 * Displays the fraud detection workflow as an interactive graph
 * @param {Object} props - Component props
 * @param {Object} props.executorStates - Map of executor IDs to their current states
 * @param {Object} props.stepDetails - Real step details from backend (tool calls, outputs)
 */
function WorkflowVisualizer({ executorStates = {}, stepDetails = {} }) {
  // Popover state
  const [anchorEl, setAnchorEl] = useState(null);
  const [selectedNode, setSelectedNode] = useState(null);

  // Static descriptions for nodes (fallback)
  const nodeDescriptions = useMemo(() => ({
    alert_router: 'Routes incoming fraud alerts to specialist analysts for parallel investigation.',
    usage_pattern_executor: 'AI agent that analyzes customer data usage patterns to detect anomalies.',
    location_analysis_executor: 'AI agent that detects geographic anomalies and suspicious location patterns.',
    billing_charge_executor: 'AI agent that identifies unusual billing patterns and charge irregularities.',
    fraud_risk_aggregator: 'Combines analyses from all specialists to calculate overall risk score.',
    review_gateway: 'Human-in-the-loop checkpoint. Pauses workflow for analyst approval on high-risk cases.',
    auto_clear_executor: 'Automatically clears alerts with low risk scores (< 0.6).',
    fraud_action_executor: 'Executes the analyst-approved action (suspend, flag, or additional verification).',
    final_notification_executor: 'Sends notification to customer and internal teams about the resolution.',
  }), []);

  // Get step info from backend data or fallback
  const getStepInfo = useCallback((nodeId) => {
    const backendData = stepDetails[nodeId];
    
    if (backendData) {
      // Real data from backend
      return {
        toolCalls: backendData.tool_calls || [],
        output: backendData.output || '',
        riskScore: backendData.risk_score,
        hasRealData: true,
      };
    }
    
    // Fallback static data for nodes without backend info
    const staticToolCalls = {
      alert_router: [{ name: 'distribute_alert', result: 'Sent to 3 analysts' }],
      review_gateway: [{ name: 'wait_for_decision', result: 'Analyst decision pending' }],
      auto_clear_executor: [{ name: 'clear_alert', result: '' }],
      fraud_action_executor: [{ name: 'execute_action', result: '' }],
      final_notification_executor: [{ name: 'send_notification', result: '' }],
    };
    
    return {
      toolCalls: staticToolCalls[nodeId] || [],
      output: '',
      hasRealData: false,
    };
  }, [stepDetails]);

  // Handle node click
  const handleNodeClick = useCallback((event, node) => {
    setAnchorEl(event.target);
    setSelectedNode(node);
  }, []);

  const handleClosePopover = useCallback(() => {
    setAnchorEl(null);
    setSelectedNode(null);
  }, []);

  // Update nodes with current executor states
  const nodes = useMemo(() => {
    return initialNodes.map((node) => ({
      ...node,
      data: {
        ...node.data,
        status: executorStates[node.id] || EXECUTOR_STATES.IDLE,
      },
    }));
  }, [executorStates]);

  const [nodesState, setNodes, onNodesChange] = useNodesState(nodes);
  const [edgesState, setEdges, onEdgesChange] = useEdgesState(initialEdges);

  // Update nodes when executor states change
  useEffect(() => {
    setNodes(nodes);
  }, [nodes, setNodes]);

  // Get status icon
  const getStatusIcon = (status) => {
    if (status === 'running') return <HourglassEmptyIcon sx={{ color: '#1976d2' }} />;
    if (status === 'completed') return <CheckCircleIcon sx={{ color: '#4caf50' }} />;
    return <AccessTimeIcon sx={{ color: '#9e9e9e' }} />;
  };

  return (
    <Box sx={{ width: '100%', height: '100%' }}>
      <ReactFlow
        nodes={nodesState}
        edges={edgesState}
        onNodesChange={onNodesChange}
        onEdgesChange={onEdgesChange}
        onNodeClick={handleNodeClick}
        nodeTypes={nodeTypes}
        fitView
        fitViewOptions={{ padding: 0.2 }}
        style={{ width: '100%', height: '100%' }}
        attributionPosition="bottom-left"
      >
        <Background />
        <Controls />
        <MiniMap
          nodeColor={(node) => {
            const status = node.data.status;
            if (status === 'running') return '#1976d2';
            if (status === 'completed') return '#4caf50';
            return '#9e9e9e';
          }}
        />
      </ReactFlow>

      {/* Node Details Popover */}
      <Popover
        open={Boolean(anchorEl)}
        anchorEl={anchorEl}
        onClose={handleClosePopover}
        anchorOrigin={{
          vertical: 'center',
          horizontal: 'right',
        }}
        transformOrigin={{
          vertical: 'center',
          horizontal: 'left',
        }}
        sx={{ pointerEvents: 'auto' }}
      >
        {selectedNode && (() => {
          const stepInfo = getStepInfo(selectedNode.id);
          return (
          <Paper sx={{ p: 2, maxWidth: 400, minWidth: 300 }}>
            {/* Header */}
            <Box sx={{ display: 'flex', alignItems: 'center', gap: 1, mb: 1 }}>
              {getStatusIcon(selectedNode.data.status)}
              <Typography variant="h6" sx={{ fontSize: 16, fontWeight: 'bold' }}>
                {selectedNode.data.label}
              </Typography>
            </Box>
            
            {/* Status chip + Risk Score */}
            <Box sx={{ display: 'flex', alignItems: 'center', gap: 1, mb: 1.5 }}>
              <Chip
                label={getStatusLabel(selectedNode.data.status)}
                size="small"
                sx={{
                  backgroundColor: getNodeStatusColor(selectedNode.data.status).bg,
                  color: getNodeStatusColor(selectedNode.data.status).text,
                }}
              />
              {stepInfo.riskScore !== undefined && (
                <Chip
                  label={`Risk: ${(stepInfo.riskScore * 100).toFixed(0)}%`}
                  size="small"
                  color={stepInfo.riskScore >= 0.6 ? 'error' : 'success'}
                  variant="outlined"
                />
              )}
            </Box>

            {/* Description */}
            <Typography variant="body2" color="text.secondary" sx={{ mb: 2 }}>
              {nodeDescriptions[selectedNode.id] || selectedNode.data.description}
            </Typography>

            <Divider sx={{ mb: 1.5 }} />

            {/* Function/Tool Calls */}
            <Typography variant="subtitle2" sx={{ display: 'flex', alignItems: 'center', gap: 0.5, mb: 1 }}>
              <FunctionsIcon sx={{ fontSize: 16 }} /> 
              {stepInfo.hasRealData ? 'Tool Calls (Real)' : 'Expected Tools'}
            </Typography>
            
            {stepInfo.toolCalls.length > 0 ? (
              <List dense sx={{ py: 0, mb: 1.5 }}>
                {stepInfo.toolCalls.map((tc, idx) => (
                  <ListItem key={idx} sx={{ py: 0.5, px: 1, flexDirection: 'column', alignItems: 'flex-start' }}>
                    <Box sx={{ display: 'flex', alignItems: 'center', width: '100%' }}>
                      <ListItemIcon sx={{ minWidth: 24 }}>
                        <Box sx={{ 
                          width: 6, height: 6, borderRadius: '50%', 
                          backgroundColor: stepInfo.hasRealData ? '#4caf50' : '#9e9e9e' 
                        }} />
                      </ListItemIcon>
                      <ListItemText 
                        primary={tc.name} 
                        primaryTypographyProps={{ 
                          variant: 'body2', 
                          fontFamily: 'monospace', 
                          fontSize: 12,
                          fontWeight: 'bold',
                        }}
                      />
                    </Box>
                    {tc.result && (
                      <Paper 
                        variant="outlined" 
                        sx={{ 
                          p: 0.75, 
                          mt: 0.5, 
                          ml: 3, 
                          backgroundColor: '#f8f9fa', 
                          borderRadius: 1,
                          width: 'calc(100% - 24px)',
                        }}
                      >
                        <Typography 
                          variant="caption" 
                          sx={{ 
                            fontFamily: 'monospace', 
                            fontSize: 10, 
                            whiteSpace: 'pre-wrap',
                            wordBreak: 'break-word',
                            display: 'block',
                            maxHeight: 80,
                            overflow: 'auto',
                          }}
                        >
                          {tc.result.length > 200 ? tc.result.slice(0, 200) + '...' : tc.result}
                        </Typography>
                      </Paper>
                    )}
                  </ListItem>
                ))}
              </List>
            ) : (
              <Typography variant="body2" color="text.secondary" sx={{ mb: 1.5, fontStyle: 'italic' }}>
                No tool calls recorded
              </Typography>
            )}

            {/* Output Summary (if available) */}
            {stepInfo.output && (
              <>
                <Typography variant="subtitle2" sx={{ display: 'flex', alignItems: 'center', gap: 0.5, mb: 1 }}>
                  <OutputIcon sx={{ fontSize: 16 }} /> Analysis Output
                </Typography>
                <Paper 
                  variant="outlined" 
                  sx={{ p: 1, backgroundColor: '#f5f5f5', borderRadius: 1, maxHeight: 120, overflow: 'auto' }}
                >
                  <Typography 
                    variant="body2" 
                    sx={{ 
                      fontFamily: 'monospace', 
                      fontSize: 11, 
                      whiteSpace: 'pre-wrap',
                      wordBreak: 'break-word',
                    }}
                  >
                    {stepInfo.output}
                  </Typography>
                </Paper>
              </>
            )}
          </Paper>
        );
        })()}
      </Popover>
    </Box>
  );
}

export default WorkflowVisualizer;
