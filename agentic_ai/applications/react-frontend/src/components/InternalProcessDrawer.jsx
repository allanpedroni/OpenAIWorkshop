import React, { useRef, useEffect } from 'react';
import {
  Drawer,
  Toolbar,
  Box,
  Typography,
  Divider,
  Accordion,
  AccordionSummary,
  AccordionDetails,
  Chip,
} from '@mui/material';
import {
  Psychology as BrainIcon,
  ExpandMore as ExpandMoreIcon,
} from '@mui/icons-material';
import { OrchestratorEvent } from './OrchestratorEvent.jsx';
import { AgentEvent } from './AgentEvent.jsx';
import { scrollToRef } from '../utils/helpers.jsx';

/**
 * InternalProcessDrawer component - Left drawer showing orchestrator and agent events
 * @param {object} props
 * @param {boolean} props.open - Whether drawer is open
 * @param {Array} props.orchestratorEvents - Array of orchestrator events
 * @param {object} props.agentEvents - Object of agent events by agent ID
 * @param {Set} props.currentAgents - Set of currently active agent IDs
 */
export const InternalProcessDrawer = ({ 
  open, 
  orchestratorEvents, 
  agentEvents, 
  currentAgents 
}) => {
  const processEndRef = useRef(null);

  // Auto-scroll when events change
  useEffect(() => {
    scrollToRef(processEndRef);
  }, [orchestratorEvents, agentEvents]);

  return (
    <Drawer
      variant="persistent"
      anchor="left"
      open={open}
      sx={{
        width: open ? 400 : 0,
        flexShrink: 0,
        '& .MuiDrawer-paper': {
          width: 400,
          boxSizing: 'border-box',
        },
      }}
    >
      <Toolbar />
      <Box sx={{ p: 2, overflow: 'auto', height: '100%' }}>
        <Typography variant="h6" gutterBottom sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
          <BrainIcon color="primary" />
          Internal Process
        </Typography>
        <Divider sx={{ mb: 2 }} />

        {/* Orchestrator Events */}
        {orchestratorEvents.length > 0 && (
          <Accordion defaultExpanded>
            <AccordionSummary expandIcon={<ExpandMoreIcon />}>
              <Typography sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                <BrainIcon fontSize="small" color="primary" />
                Orchestrator ({orchestratorEvents.length})
              </Typography>
            </AccordionSummary>
            <AccordionDetails>
              <Box sx={{ display: 'flex', flexDirection: 'column', gap: 1 }}>
                {orchestratorEvents.map((event, idx) => (
                  <OrchestratorEvent key={idx} event={event} />
                ))}
              </Box>
            </AccordionDetails>
          </Accordion>
        )}

        {/* Agent Events - Show messages in internal process */}
        {Object.entries(agentEvents)
          .filter(([agentId, agentData]) => agentData.showMessageInInternalProcess !== false)
          .map(([agentId, agentData]) => (
            <AgentEvent
              key={agentId}
              agentId={agentId}
              agentData={agentData}
              isActive={currentAgents.has(agentId)}
            />
          ))}

        {/* Tool Calls for agents that don't show messages */}
        {Object.entries(agentEvents)
          .filter(([agentId, agentData]) => 
            agentData.showMessageInInternalProcess === false && 
            agentData.toolCallsByTurn && 
            Object.keys(agentData.toolCallsByTurn).length > 0
          )
          .map(([agentId, agentData]) => (
            <Accordion key={agentId} defaultExpanded>
              <AccordionSummary expandIcon={<ExpandMoreIcon />}>
                <Typography sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                  🔧 Tool Calls
                </Typography>
              </AccordionSummary>
              <AccordionDetails>
                <Box>
                  {Object.entries(agentData.toolCallsByTurn)
                    .sort(([turnA], [turnB]) => Number(turnA) - Number(turnB))
                    .map(([turn, tools]) => (
                      <Box key={turn} sx={{ mb: 1 }}>
                        <Typography variant="caption" sx={{ color: 'text.secondary', display: 'block', mb: 0.5 }}>
                          Turn {turn}:
                        </Typography>
                        <Box sx={{ display: 'flex', gap: 0.5, flexWrap: 'wrap', ml: 1 }}>
                          {tools.map((tool, idx) => (
                            <Chip
                              key={idx}
                              label={`🔧 ${tool}`}
                              size="small"
                              variant="outlined"
                              color="info"
                            />
                          ))}
                        </Box>
                      </Box>
                    ))}
                </Box>
              </AccordionDetails>
            </Accordion>
          ))}

        <div ref={processEndRef} />
      </Box>
    </Drawer>
  );
};
